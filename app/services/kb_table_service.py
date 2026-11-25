# -*- coding: utf-8 -*-
"""
知识库表格保真解析服务
======================
从 PDF / Word / Excel 中"结构化"地抽取表格，而不是把文件拍平成纯文本。

设计原则（对应需求）：
  1. 保真：只记录文件里真实存在的单元格内容，绝不推测、不补全、不生成。
  2. 可追溯：每张表记录来源文档、页码/Sheet、行列数，回答时可标注出处。
  3. 可核对：抽取后计算"非空单元格占比"作为解析质量参考，供人工复核。

抽取结果统一为 dict：
  {
    "table_name":  str,   # 表格名称（Excel 用 Sheet 名，PDF 用 "第N页-表格M"）
    "source":      str,   # 来源描述（页码 / Sheet / 表格序号）
    "rows":        [[str, ...], ...],  # 原始单元格文本，行列结构与文件一致
    "row_count":   int,
    "col_count":   int,
    "fill_rate":   float, # 非空单元格占比 0~1，解析质量参考
  }

注意：本模块只做"抽取"，不做"生成"。下载时返回的是上传的原文件本身。
"""
import logging
import os
import re

logger = logging.getLogger(__name__)

MAX_TABLES_PER_DOC = 50       # 单文档最多抽取表格数，防止异常文件拖垮服务
MAX_CELLS_PER_TABLE = 5000    # 单表最多单元格数


def _clean(cell):
    """把单元格内容规整为字符串；None → 空串，避免 None 进 JSON 出错。"""
    if cell is None:
        return ''
    if isinstance(cell, float) and cell.is_integer():
        return str(int(cell))
    s = str(cell).strip()
    s = re.sub(r'[ \t]+', ' ', s)
    return s


def _table_stats(rows):
    """计算行数/列数/非空占比，作为解析质量的可核对指标。"""
    rows = [[_clean(c) for c in row] for row in rows]
    rows = [r for r in rows if any(r)]           # 丢掉全空行
    if not rows:
        return rows, 0, 0, 0.0
    col_count = max(len(r) for r in rows)
    rows = [r + [''] * (col_count - len(r)) for r in rows]
    total = sum(len(r) for r in rows)
    filled = sum(1 for r in rows for c in r if c)
    return rows, len(rows), col_count, round(filled / total, 4) if total else 0.0


def _make(name, source, rows):
    rows, rc, cc, fill = _table_stats(rows)
    if not rc or not cc or rc * cc > MAX_CELLS_PER_TABLE:
        return None
    return {
        'table_name': name,
        'source': source,
        'rows': rows,
        'row_count': rc,
        'col_count': cc,
        'fill_rate': fill,
    }


def extract_from_docx(filepath):
    """Word：用 python-docx 读取 doc.tables，逐单元格抽取。"""
    tables = []
    try:
        from docx import Document
        doc = Document(filepath)
    except Exception as e:
        logger.warning('[表格抽取] Word 打开失败: %s', e)
        return tables
    for i, t in enumerate(doc.tables[:MAX_TABLES_PER_DOC], 1):
        try:
            rows = [[c.text for c in row.cells] for row in t.rows]
            item = _make('表格 %d' % i, 'Word 第 %d 个表格' % i, rows)
            if item:
                tables.append(item)
        except Exception as e:
            logger.warning('[表格抽取] Word 第 %d 个表格失败: %s', i, e)
    return tables


def extract_from_xlsx(filepath):
    """Excel：用 openpyxl 读取每个 Sheet 的单元格值。"""
    tables = []
    try:
        from openpyxl import load_workbook
        wb = load_workbook(filepath, data_only=True, read_only=True)
    except Exception as e:
        logger.warning('[表格抽取] Excel 打开失败: %s', e)
        return tables
    try:
        for ws in wb.worksheets[:MAX_TABLES_PER_DOC]:
            try:
                rows = []
                for r in ws.iter_rows(values_only=True):
                    rows.append(list(r))
                    if len(rows) > MAX_CELLS_PER_TABLE:
                        break
                item = _make(ws.title, 'Excel Sheet：%s' % ws.title, rows)
                if item:
                    tables.append(item)
            except Exception as e:
                logger.warning('[表格抽取] Sheet %s 失败: %s', ws.title, e)
    finally:
        try:
            wb.close()
        except Exception:
            pass
    return tables


def extract_from_pdf(filepath):
    """PDF：用 PyMuPDF 的 find_tables() 识别表格线框，逐单元格抽取。"""
    tables = []
    try:
        import pymupdf
        doc = pymupdf.open(filepath)
    except Exception as e:
        logger.warning('[表格抽取] PDF 打开失败: %s', e)
        return tables
    try:
        idx = 0
        for pno, page in enumerate(doc, 1):
            if idx >= MAX_TABLES_PER_DOC:
                break
            try:
                found = page.find_tables()
            except Exception as e:
                logger.warning('[表格抽取] PDF 第 %d 页识别失败: %s', pno, e)
                continue
            for t in found.tables:
                idx += 1
                if idx > MAX_TABLES_PER_DOC:
                    break
                try:
                    item = _make('第%d页-表格%d' % (pno, idx),
                                 'PDF 第 %d 页第 %d 个表格' % (pno, idx),
                                 t.extract())
                    if item:
                        tables.append(item)
                except Exception as e:
                    logger.warning('[表格抽取] PDF 第 %d 页第 %d 表失败: %s', pno, idx, e)
    finally:
        try:
            doc.close()
        except Exception:
            pass
    return tables


def extract_tables(filepath, filename):
    """按扩展名分发，返回结构化表格列表。"""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext == 'docx':
        return extract_from_docx(filepath)
    if ext in ('xlsx', 'xlsm'):
        return extract_from_xlsx(filepath)
    if ext == 'pdf':
        return extract_from_pdf(filepath)
    return []


def tables_to_text(tables):
    """把结构化表格转成可读文本，供向量检索使用（保留行列语义）。"""
    parts = []
    for t in tables:
        lines = ['【表格：%s（%d行×%d列，来源：%s）】'
                 % (t['table_name'], t['row_count'], t['col_count'], t['source'])]
        for row in t['rows']:
            lines.append(' | '.join(row))
        parts.append('\n'.join(lines))
    return '\n\n'.join(parts)


# ---- 问答：意图识别与真实表格匹配 ----

# 明确的"索取文件"动作词（只有这些才算强意图，单纯提到"表"不算）
_WANT_WORDS = ('下载', '发我', '给我', '要一份', '来一份', '导出', '发一份', '拿一份', 'excel', 'xlsx')
# 问内容而非要文件的信号
_ASK_ONLY_WORDS = ('表格里', '表中', '表里', '这张表', '该表的', '表格中', '表里写', '表格内容')

# 问题里的口语噪音，匹配前剔除，避免稀释相似度
_NOISE = (
    '我需要', '我要', '我想找', '我想', '请给我', '帮我', '麻烦', '请问', '能不能',
    '有没有', '给我', '发我', '下载', '导出', '要一份', '来一份', '发一份', '拿一份',
    '一份', '这个', '那个', '一下', '看看', '查询', '是否', '提供', '找一下',
    '的表格', '表格', '清单', '明细', '文件', '可以吗', '谢谢', '请', '吗', '呢',
)
# 文档名里的编号前缀（QR-JY-012-2023 / WI-AH-096-2026 A2 等）不参与语义匹配
_DOC_NO_RE = re.compile(r'^[A-Za-z]{1,6}(?:[\-–—_][A-Za-z0-9]{1,8}){1,6}\s*')
_EXT_RE = re.compile(r'\.(docx?|xlsx?|xlsm|pdf|txt|md|csv)$', re.I)
_PUNCT_RE = re.compile(r'[\s（）()【】\[\]《》,，。.!！?？、:：;；\-_/\\|]')


def wants_table(query):
    """判断用户是否在明确索要表格文件（只看动作词，不做生成）。"""
    if not query:
        return False
    q = query.strip().lower()
    if not any(w in q for w in _WANT_WORDS):
        return False
    # "表格里写了什么"这类问内容的话，即使带"表"也不算索取
    if any(w in q for w in _ASK_ONLY_WORDS):
        return False
    return True


def _norm(s):
    """归一化：去标点空白、保留中文与字母数字（不剥"表"字，它是关键语义）。"""
    return _PUNCT_RE.sub('', (s or '').lower())


def _strip_doc_name(s):
    """去掉扩展名和文档编号前缀，留下可读的语义名。"""
    s = _EXT_RE.sub('', (s or '').strip())
    s = _DOC_NO_RE.sub('', s)
    return s.strip()


def _core_query(query):
    """剔除口语噪音，得到用于匹配的核心词。"""
    x = _norm(query)
    for w in sorted(_NOISE, key=len, reverse=True):
        x = x.replace(_norm(w), '')
    return x


def _bigrams(s):
    if len(s) < 2:
        return [s] if s else []
    return [s[i:i + 2] for i in range(len(s) - 1)]


def _dice(a, b):
    """中文 2-gram Dice 相似度，0~1。"""
    A, B = set(_bigrams(a)), set(_bigrams(b))
    if not A or not B:
        return 0.0
    return 2.0 * len(A & B) / (len(A) + len(B))


def _table_fields(t):
    """取表格的可匹配字段：表格名、文档语义名、表头/内容关键词。"""
    if isinstance(t, dict):
        get = lambda k, d='': t.get(k, d)
        rows = t.get('rows') or []
    else:
        get = lambda k, d='': getattr(t, k, d)
        rows = t.rows()
    name = _norm(_strip_doc_name(get('table_name')))
    doc = _norm(_strip_doc_name(get('doc_name')))
    # 取前几行里较短的单元格作为内容特征（长段落会稀释相似度）
    cells = []
    for row in rows[:3]:
        for cell in row:
            c = str(cell).strip()
            if 0 < len(c) <= 20:
                cells.append(c)
    content = _norm(' '.join(cells[:20]))
    return name, doc, content


def match_table(query, tables, min_score=0.42):
    """在真实表格列表里匹配用户可能需要的表格。

    综合表格名、文档语义名（去掉编号）、表格内容三处做 2-gram 相似度打分。
    tables: [dict|KBTable]。返回 (table, score)，未命中返回 (None, 0)。
    只匹配已存在的表格，绝不构造新表格。
    """
    if not query or not tables:
        return None, 0.0
    core = _core_query(query)
    if len(core) < 2:
        return None, 0.0

    best, best_score = None, 0.0
    for t in tables:
        name, doc, content = _table_fields(t)
        scores = []
        # 文档语义名最关键：顾客满意度调查表.docx → 顾客满意度调查表
        if doc:
            s = _dice(core, doc)
            if core in doc or doc in core:
                s = max(s, 0.92)
            scores.append(s * 1.0)
        # 表格名（"表格 1"这种默认值相似度天然低，不会误命中）
        if name and name != '1':
            s = _dice(core, name)
            if core in name:
                s = max(s, 0.9)
            scores.append(s * 0.95)
        # 内容兜底，权重低
        if content:
            scores.append(_dice(core, content) * 0.6)
        score = max(scores) if scores else 0.0
        if score > best_score:
            best, best_score = t, score

    return (best, best_score) if best_score >= min_score else (None, best_score)


def table_hit_payload(table, base_url='/api/v1'):
    """构造给前端的表格命中提示（只含真实文件的下载链接）。"""
    tid = table.get('id') if isinstance(table, dict) else table.id
    name = table.get('table_name', '') if isinstance(table, dict) else table.table_name
    doc = table.get('doc_name', '') if isinstance(table, dict) else table.doc_name
    kb_id = table.get('kb_id', '') if isinstance(table, dict) else table.kb_id
    # 默认名"表格 N"对用户无意义，改用文档名作为卡片标题
    if re.match(r'^表格\s*\d+$', name or '') and doc:
        name = re.sub(r'\.[^.]+$', '', doc)
    return {
        '__table_card__': {
            'table_id': tid,
            'table_name': name,
            'doc_name': doc,
            'url': '%s/kb/%s/tables/%s/download' % (base_url, kb_id, tid),
        }
    }


def table_summary(tables):
    """生成表格抽取质量摘要，供上传结果和前端核对。"""
    return {
        'table_count': len(tables),
        'tables': [
            {
                'table_name': t['table_name'],
                'source': t['source'],
                'row_count': t['row_count'],
                'col_count': t['col_count'],
                'fill_rate': t['fill_rate'],
            }
            for t in tables
        ],
    }
