# -*- coding: utf-8 -*-
"""
扫描版 PDF 的 OCR 兜底解析
==========================
用于 PyPDF2 提取不到文字层时，把 PDF 页面渲染成图片再做中文 OCR。

依赖：
  - pymupdf：把 PDF 页面渲染为位图
  - rapidocr_onnxruntime：本地中文 OCR，模型随包提供，不需要联网

设计要点：
  - OCR 引擎单例，避免每次上传都重复加载模型
  - 最多处理前 20 页，避免超大文件长时间阻塞请求
  - 任何依赖缺失或识别失败都返回可读的 [错误] 文本，由上传接口转成 400
"""
import logging

logger = logging.getLogger(__name__)

MAX_PAGES = 20
RENDER_SCALE = 2.0  # 约 144 DPI，扫描件正文识别效果与速度的平衡点

_engine = None
_engine_failed = False


def get_engine():
    """获取 RapidOCR 单例；不可用时返回 None"""
    global _engine, _engine_failed
    if _engine is not None:
        return _engine
    if _engine_failed:
        return None
    try:
        from rapidocr_onnxruntime import RapidOCR
        _engine = RapidOCR()
        return _engine
    except Exception as e:
        logger.warning('[PDF OCR] RapidOCR 初始化失败: %s', e)
        _engine_failed = True
        return None


def _get_fitz():
    """兼容 pymupdf 2.x 与旧版 fitz 包名"""
    try:
        import pymupdf as fitz
        return fitz
    except ImportError:
        pass
    try:
        import fitz
        return fitz
    except ImportError:
        return None


def extract_text(filepath, max_pages=MAX_PAGES, scale=RENDER_SCALE):
    """
    对 PDF 做 OCR，返回按页拼接的纯文本。
    依赖缺失或识别失败时返回以 '[错误]' 开头的提示文本。
    """
    fitz = _get_fitz()
    if fitz is None:
        return '[错误] 未安装 PyMuPDF，无法识别扫描版 PDF。请运行 pip install pymupdf'

    engine = get_engine()
    if engine is None:
        return '[错误] 未安装 RapidOCR，无法识别扫描版 PDF。请运行 pip install rapidocr_onnxruntime'

    try:
        import numpy as np
    except ImportError:
        return '[错误] 未安装 NumPy，无法识别扫描版 PDF。请运行 pip install numpy'

    doc = None
    try:
        doc = fitz.open(filepath)
        pages = []
        for index, page in enumerate(doc):
            if index >= max_pages:
                break
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            result, _ = engine(image)
            lines = []
            for item in result or []:
                if len(item) >= 2 and isinstance(item[1], str):
                    line = item[1].strip()
                    if line:
                        lines.append(line)
            if lines:
                pages.append('\n'.join(lines))
        return '\n\n'.join(pages)
    except Exception as e:
        logger.exception('[PDF OCR] 识别失败: %s', filepath)
        return '[错误] 扫描版 PDF OCR 失败：%s' % e
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass
