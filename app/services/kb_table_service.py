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
    """把单元格内容规整为字符串；None → 空串，避免 None 进 JSON 出错。

    注意 PyMuPDF find_tables() 会把空单元格返回成字符串 "None"/"nan"，
    必须一并视为空，否则页眉行残留、空列删不掉、完整度被稀释。
    """
    if cell is None:
        return ''
    if isinstance(cell, float) and cell.is_integer():
        return str(int(cell))
    s = str(cell).strip()
    if s.lower() in ('none', 'nan', 'null'):
        return ''
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


def rebuild_docx_table(table):
    """从 Word 表格底层 XML 按 gridSpan/vMerge 重建真实网格。

    python-docx 的 row.cells 会把合并单元格在每个网格位置重复返回，
    导致预览里出现 6 列相同文字。这里直接遍历 w:tc，用 gridSpan（跨列）
    与 vMerge（跨行）还原：被合并覆盖的位置用 None 占位，返回
    (rows, merges)，其中 merges=[{row,col,rowspan,colspan,text}]。
    """
    from docx.oxml.ns import qn
    ncol = len(table.columns)
    if not ncol:
        return None
    rows, merges = [], []
    vmerge_open = {}   # col -> {'row': 起始行, 'text': 文字}
    for ri, tr in enumerate(table._tbl.findall(qn('w:tr'))):
        row = [None] * ncol
        ci = 0
        for tc in tr.findall(qn('w:tc')):
            while ci < ncol and row[ci] is not None:
                ci += 1
            if ci >= ncol:
                break
            tcPr = tc.find(qn('w:tcPr'))
            gs, vm = 1, None
            if tcPr is not None:
                g = tcPr.find(qn('w:gridSpan'))
                v = tcPr.find(qn('w:vMerge'))
                if g is not None:
                    gs = max(1, int(g.get(qn('w:val')) or 1))
                if v is not None:
                    vm = v.get(qn('w:val')) or 'continue'
            text = ''.join(t.text or '' for t in tc.findall('.//' + qn('w:t'))).strip()
            if vm == 'continue':
                # 纵向合并的延续格：整段占位 None，span 在 restart 时回填
                for c in range(ci, min(ci + gs, ncol)):
                    row[c] = None
                ci += gs
                continue
            # 先结算上一行遗留的纵向合并（restart 或普通格都意味着上一段结束）
            for c, info in list(vmerge_open.items()):
                span = ri - info['row']
                if span > 1:
                    merges.append({'row': info['row'], 'col': c,
                                   'rowspan': span, 'colspan': 1,
                                   'text': info['text']})
            vmerge_open = {}
            for c in range(ci, min(ci + gs, ncol)):
                row[c] = None            # 被本格覆盖的位置
            row[ci] = text
            if gs > 1:
                merges.append({'row': ri, 'col': ci,
                               'rowspan': 1, 'colspan': gs, 'text': text})
            if vm == 'restart':
                for c in range(ci, min(ci + gs, ncol)):
                    vmerge_open[c] = {'row': ri, 'text': text}
            ci += gs
        rows.append(row)
    # 收尾：最后一段纵向合并
    for c, info in vmerge_open.items():
        span = len(rows) - info['row']
        if span > 1:
            merges.append({'row': info['row'], 'col': c,
                           'rowspan': span, 'colspan': 1, 'text': info['text']})
    return rows, merges


def extract_from_docx(filepath):
    """Word：从底层 XML 重建网格，保留横向/纵向合并单元格。"""
    tables = []
    try:
        from docx import Document
        doc = Document(filepath)
    except Exception as e:
        logger.warning('[表格抽取] Word 打开失败: %s', e)
        return tables
    for i, t in enumerate(doc.tables[:MAX_TABLES_PER_DOC], 1):
        try:
            rebuilt = rebuild_docx_table(t)
            if not rebuilt:
                continue
            rows, merges = rebuilt
            text_rows = [[('' if c is None else c) for c in r] for r in rows]
            item = _make('表格 %d' % i, 'Word 第 %d 个表格' % i, text_rows)
            if not item:
                continue
            # 完整度按"有效网格"算：合并覆盖位(None)不计入分母，避免虚低
            covered = set()
            for m in merges:
                for rr in range(m['row'], m['row'] + m['rowspan']):
                    for cc in range(m['col'], m['col'] + m['colspan']):
                        covered.add((rr, cc))
            slots = [(r, c) for r in range(len(rows)) for c in range(len(rows[r]))
                     if (r, c) not in covered]
            filled = sum(1 for r, c in slots
                         if rows[r][c] is not None and str(rows[r][c]).strip())
            item['fill_rate'] = round(filled / len(slots), 4) if slots else 1.0
            item['rows'] = rows          # 保留 None 合并占位
            item['merges'] = merges
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


# ---- PDF 伪表格过滤 ----
# 文档每页的页眉/页脚/审批栏里的固定字段，属于"记录信息"而非数据表。
# 用户明确要求：这类内容只作为正文文字用于检索，不算表格、不出现在表格清单/推荐里。
_RECORD_FIELDS = ('文件编号', '生效日期', '编制', '审核', '批准', '会签', '文件发放')
_PAGE_MARK_RE = re.compile(r'第\s*\d+\s*页|共\s*\d+\s*页')


def _is_record_like_table(rows, fill_rate):
    """判定 PDF 中由页眉/审批栏/正文框线造成的伪表格。

    返回 True 表示应过滤掉（不进 kb_tables，但仍留在正文文本里供检索）。
    只用于 PDF —— Word 的 doc.tables 和 Excel 的 Sheet 本身就是真表格。

    判定规则（对 WI-AH-098-2024A0 环境制度汇编等受控文件验证过）：
      1. 页眉表：出现 >=2 个记录字段 + 页码标记，且只有 1~3 行；
      2. 审批/发放记录表：出现 >=2 个签署字段 + 内容稀疏(fill<0.5) + 行数<=12；
      3. 正文被框线误识别：行数>=5 但内容极稀疏(fill<0.35)。
    真正的业务数据表（有表头+多行业务数据，如"序号/文件名称/页码"、
    "序号/费用类别/说明"）字段命中为 0、完整度较高，会被保留。
    """
    flat = ' '.join(str(c) for row in rows for c in row)
    field_hits = sum(1 for w in _RECORD_FIELDS if w in flat)
    # 1) 页眉表：编号 / 生效日期 / 第X页 共Y页，通常只有两行
    if field_hits >= 2 and len(rows) <= 3 and _PAGE_MARK_RE.search(flat):
        return True
    # 2) 审批栏 / 文件发放记录：签署字段多，但大多是待填写的空格
    if field_hits >= 2 and fill_rate < 0.5 and len(rows) <= 12:
        return True
    # 3) 正文段落被表格框线框住：行多但内容极稀疏
    if len(rows) >= 5 and fill_rate < 0.35:
        return True
    return False


def _is_header_row(row):
    """判断是否为页眉/页脚记录行（非业务数据行）。

    受控文件的表格里常被框进页眉行，例如：
      ['','','环境保护制度汇编','','']  /  ['文件编号','QP…','生效日期','2024…','第28页 共57页']
    这类行要剔除，否则整张表会被误判成页眉表或完整度被稀释。
    """
    cells = [_clean(c) for c in row]
    cells = [c for c in cells if c]
    if not cells:
        return False  # 全空行交给 _table_stats 处理
    flat = ' '.join(cells)
    hits = sum(1 for w in _RECORD_FIELDS if w in flat)
    if hits >= 2 or (hits >= 1 and _PAGE_MARK_RE.search(flat)):
        return True
    # 只有一个非空单元格且是文档标题（如"环境保护制度汇编"）
    if len(cells) == 1 and len(cells[0]) <= 24 and (
            '汇编' in cells[0] or '制度' in cells[0] or '手册' in cells[0]):
        return True
    return False


def _drop_empty_columns(rows):
    """删除整列都是空的行列（跨页续表被框成 9 列时，有效数据只在 3 列）。"""
    if not rows:
        return rows
    width = max(len(r) for r in rows)
    rows = [[_clean(c) for c in r] + [''] * (width - len(r)) for r in rows]
    keep = [i for i in range(width) if any(r[i] for r in rows)]
    if not keep:
        return []
    return [[r[i] for i in keep] for r in rows]


def _clean_pdf_rows(raw_rows):
    """清洗 PDF 表格：剔除页眉行 + 去掉全空列，保留真实数据行列结构。"""
    rows = [[_clean(c) for c in r] for r in raw_rows]
    rows = [r for r in rows if not _is_header_row(r)]
    return _drop_empty_columns(rows)


def _cluster_bounds(vals, tol=1.5):
    """把相近的坐标聚成一条边界线（PDF 浮点坐标有微小误差）。"""
    vals = sorted(set(round(v, 1) for v in vals))
    groups = []
    for v in vals:
        if not groups or v - groups[-1][-1] > tol:
            groups.append([v])
        else:
            groups[-1].append(v)
    return [round(sum(g) / len(g), 1) for g in groups]


def rebuild_pdf_table(page, table, tol=1.5):
    """用单元格 bbox + 页面文本层重建表格（比 extract() 更准确）。

    PyMuPDF 的 find_tables().extract() 有两个缺陷：
      1. 会把标点从词中剥离、堆到单元格末尾（"1.环境…（含服务年费）" → "1 环境…） ."）；
      2. 丢失合并单元格信息（跨行格只在首行写值，其余为空）。
    而 page.get_textbox(cell_bbox) 取到的文字标点正确，table.cells 的 bbox 尺寸
    能反映合并（跨行格的 bbox 高度是普通行的数倍）。

    返回 (rows, merges):
      rows   —— 二维矩阵，被合并覆盖的格子用 None 占位；
      merges —— [{'row','col','rowspan','colspan','text'}]，供前端渲染合并格。
    """
    try:
        import pymupdf
    except ImportError:
        return None
    cells = [c for c in (table.cells or []) if c]
    if not cells:
        return None
    ys = _cluster_bounds([c[1] for c in cells] + [c[3] for c in cells], tol)
    xs = _cluster_bounds([c[0] for c in cells] + [c[2] for c in cells], tol)

    def idx(v, axis):
        return min(range(len(axis)), key=lambda i: abs(axis[i] - v))

    grid = {}
    for c in cells:
        r0, r1 = idx(c[1], ys), idx(c[3], ys)
        c0, c1 = idx(c[0], xs), idx(c[2], xs)
        try:
            text = ' '.join(page.get_textbox(pymupdf.Rect(c)).split())
        except Exception:
            text = ''
        grid[(r0, c0)] = {
            'text': text,
            'rs': max(1, r1 - r0),
            'cs': max(1, c1 - c0),
        }
    nrow, ncol = len(ys) - 1, len(xs) - 1
    if nrow <= 0 or ncol <= 0:
        return None
    rows, merges, occupied = [], [], set()
    for r in range(nrow):
        row = []
        for c in range(ncol):
            if (r, c) in occupied:
                row.append(None)          # 被上方/左方合并格覆盖
                continue
            cell = grid.get((r, c))
            if not cell:
                row.append('')
                continue
            rs, cs = cell['rs'], cell['cs']
            for rr in range(r, min(r + rs, nrow)):
                for cc in range(c, min(c + cs, ncol)):
                    occupied.add((rr, cc))
            if (rs > 1 or cs > 1) and cell['text']:
                merges.append({'row': r, 'col': c, 'rowspan': rs,
                               'colspan': cs, 'text': cell['text']})
            row.append(cell['text'])
        rows.append(row)
    return rows, merges


def _first_col_numbers(rows):
    """取首列中能解析为序号的整数，返回 (序号列表, 占比)。"""
    vals = []
    for r in rows:
        if not r:
            continue
        s = str(r[0]).strip()
        m = re.match(r'^(\d+)$', s)
        if m:
            vals.append(int(m.group(1)))
    ratio = len(vals) / len(rows) if rows else 0
    return vals, ratio


def _is_continuation(prev, cur):
    """判断 cur 是否为 prev 的跨页续表：列数一致、首列序号递增延续。"""
    if not prev or not cur:
        return False
    if prev['col_count'] != cur['col_count']:
        return False
    pv, pr = _first_col_numbers(prev['rows'])
    cv, cr = _first_col_numbers(cur['rows'])
    if pr < 0.6 or cr < 0.6 or not pv or not cv:
        return False
    # 续表首序号 > 前表末序号，且不从头（1）重新编号
    return cv[0] > pv[-1] and cv[0] > 1


# ---- 页眉横幅 / 审批栏判定（通用，不限文档模板） ----
# 公司名特征：页眉横幅几乎必带公司全称或英文名
_COMPANY_HINTS = ('有限公司', '有限责任公司', '股份有限公司', 'LTD', 'CO.')
# 签署类字段：审批栏特征（比 _RECORD_FIELDS 更聚焦）
_SIGN_FIELDS = ('编制', '审核', '批准', '会签', '文件发放')


def _first_col_digit_ratio(rows):
    """首列以数字开头的行占比（数据表通常有序号列，页眉/审批栏没有）。"""
    checked, digit = 0, 0
    for r in rows:
        if not r:
            continue
        s = str(r[0]).strip()
        if not s:
            continue
        checked += 1
        if re.match(r'^\d+', s):
            digit += 1
    return digit / checked if checked else 0.0


def _looks_like_header_banner(rows, doc_name):
    """页眉横幅：公司名 + 文档标题的组合，行数极少且无序号列。

    例：['鹤壁市宝瑞德化工有限公司 HEBI BREAD CHEMICALS CO.,LTD', '危险废物管理制度']
    判定：行数<=2、首列无数字序号，且任一单元格与文档语义名高度相似，
    或含公司名特征词。
    """
    if not rows or len(rows) > 2:
        return False
    if _first_col_digit_ratio(rows) >= 0.5:
        return False
    doc_sem = _norm(_strip_doc_name(doc_name)) if doc_name else ''
    for r in rows:
        for c in r:
            cell = _norm('' if c is None else str(c))
            if not cell:
                continue
            if doc_sem and (cell in doc_sem or doc_sem in cell
                            or _dice(cell, doc_sem) >= 0.7):
                return True
            if any(h.lower() in cell for h in _COMPANY_HINTS):
                return True
    return False


def _is_sign_block(rows):
    """审批/签署栏：出现 >=2 个签署字段，且至少 2 行的行首格是签署字段。

    例：编制/日期、审核/日期、批准/日期、文件发放。
    不看首列数字占比——审批栏常与"修订记录"等数字序号段连在一起，
    会被序号干扰漏网；行首签署格才是稳定特征。
    """
    flat = ' '.join('' if c is None else str(c) for r in rows for c in r)
    hits = sum(1 for w in _SIGN_FIELDS if w in flat)
    if hits < 2:
        return False
    lead_hits = 0
    for r in rows:
        cells = ['' if c is None else str(c).strip() for c in r]
        cells = [c for c in cells if c]
        if cells and any(cells[0].startswith(w) for w in _SIGN_FIELDS):
            lead_hits += 1
    return lead_hits >= 2


def _prepare_pdf_table(page, table, doc_name=None):
    """重建单页表格并清洗：返回 (rows, merges)，或 None。

    - 用 bbox+文本层重建（标点正确、保留合并格占位 None）；
    - 剔除页眉行；
    - 去掉全空列，并同步重映射合并格的列索引；
    - 判定有效性（纯页眉/审批/稀疏框线表返回 None）。
    """
    try:
        import pymupdf
    except ImportError:
        return None
    rebuilt = rebuild_pdf_table(page, table)
    if not rebuilt:
        return None
    rows, merges = rebuilt
    # 剔除页眉行，同时偏移其下方合并格的行号
    keep_idx = [i for i, r in enumerate(rows)
                if not _is_header_row([('' if c is None else c) for c in r])]
    if not keep_idx:
        return None
    idx_map = {old: new for new, old in enumerate(keep_idx)}
    rows = [list(rows[i]) for i in keep_idx]
    merges = [dict(m, row=idx_map[m['row']]) for m in merges if m['row'] in idx_map]

    # 去掉全空列（None 视为空），并同步压缩合并格的列/跨列数
    width = max((len(r) for r in rows), default=0)
    rows = [list(r) + [None] * (width - len(r)) for r in rows]
    keep_cols = [i for i in range(width)
                 if any(('' if r[i] is None else r[i]).strip() for r in rows)]
    if not keep_cols:
        return None
    col_map = {old: new for new, old in enumerate(keep_cols)}
    new_rows = [[r[i] for i in keep_cols] for r in rows]
    new_merges = []
    for m in merges:
        if m['col'] not in col_map:
            continue
        # 该合并格覆盖的列里，被保留下来的列数决定新的 colspan
        covered = [c for c in range(m['col'], m['col'] + m['colspan']) if c in col_map]
        if not covered:
            continue
        new_merges.append(dict(m, col=col_map[m['col']], colspan=len(covered)))

    # 有效性判定（用非 None 文本计算完整度）
    text_rows = [[('' if c is None else c) for c in r] for r in new_rows]
    filled = sum(1 for r in text_rows for c in r if c.strip())
    total = sum(len(r) for r in text_rows)
    fill = round(filled / total, 4) if total else 0.0
    if not text_rows or not any(any(c.strip() for c in r) for r in text_rows):
        return None
    if _is_record_like_table(text_rows, fill):
        return None
    if _looks_like_header_banner(text_rows, doc_name):
        return None
    if _is_sign_block(text_rows):
        return None
    return new_rows, new_merges, fill


def extract_from_pdf(filepath, filename=None):
    """PDF：从单元格 bbox + 页面文本层重建表格（标点正确、保留合并格）。

    处理流程：
      1. bbox 重建：修正 extract() 的标点错位，保留合并单元格；
      2. 剔除页眉行、去除全空列；
      3. 过滤纯页眉/审批/框线/页眉横幅伪表格（含跨页重复兜底）；
      4. 合并跨页续表（第27页序号1-11 + 第28页序号12-29 → 一张完整表），
         并同步偏移合并格行号。
    """
    tables = []
    try:
        import pymupdf
        doc = pymupdf.open(filepath)
    except Exception as e:
        logger.warning('[表格抽取] PDF 打开失败: %s', e)
        return tables
    pending = []
    try:
        for pno, page in enumerate(doc, 1):
            try:
                found = page.find_tables()
            except Exception as e:
                logger.warning('[表格抽取] PDF 第 %d 页识别失败: %s', pno, e)
                continue
            for t in found.tables:
                try:
                    prepared = _prepare_pdf_table(page, t, doc_name=filename)
                    if not prepared:
                        continue
                    rows, merges, fill = prepared
                    rc, cc = len(rows), max((len(r) for r in rows), default=0)
                    if not rc or not cc or rc * cc > MAX_CELLS_PER_TABLE:
                        continue
                    pending.append({'page': pno, 'rows': rows, 'merges': merges,
                                    'row_count': rc, 'col_count': cc, 'fill_rate': fill})
                except Exception as e:
                    logger.warning('[表格抽取] PDF 第 %d 页表格处理失败: %s', pno, e)
    finally:
        try:
            doc.close()
        except Exception:
            pass

    # 跨页重复兜底：相同内容出现在 >=2 个不同页且行数<=3，几乎必是页眉横幅
    if len(pending) > 1:
        seen_pages = {}
        for item in pending:
            if item['row_count'] > 3:
                continue
            key = tuple(
                tuple('' if c is None else str(c).strip() for c in r)
                for r in item['rows'])
            seen_pages.setdefault(key, set()).add(item['page'])
        repeated = {k for k, pages in seen_pages.items() if len(pages) >= 2}
        if repeated:
            before = len(pending)
            pending = [it for it in pending if it['row_count'] > 3
                       or tuple(tuple('' if c is None else str(c).strip() for c in r)
                                for r in it['rows']) not in repeated]
            if before != len(pending):
                logger.info('[表格抽取] 过滤跨页重复页眉 %d 张', before - len(pending))

    # 合并跨页续表：相邻页、列数一致、序号延续；合并格行号整体偏移
    merged = []
    for item in pending:
        pno = item['page']
        if merged and pno == merged[-1]['pages'][-1] + 1 and _is_continuation(merged[-1], item):
            prev = merged[-1]
            offset = len(prev['rows'])
            prev['rows'].extend(item['rows'])
            prev['merges'].extend([dict(m, row=m['row'] + offset) for m in item['merges']])
            prev['pages'].append(pno)
            # 独立统计：不能用 _table_stats（它会把 None 合并占位冲成空串）
            rc = len(prev['rows'])
            cc = max((len(r) for r in prev['rows']), default=0)
            filled = sum(1 for r in prev['rows'] for c in r if c is not None and str(c).strip())
            fill = round(filled / (rc * cc), 4) if rc and cc else 0.0
            prev.update(row_count=rc, col_count=cc, fill_rate=fill)
            logger.info('[表格抽取] 合并跨页续表：第 %s 页 → 共 %d 行',
                        '-'.join(str(p) for p in prev['pages']), rc)
        else:
            merged.append({'pages': [pno], 'rows': list(item['rows']),
                           'merges': list(item['merges']),
                           'row_count': item['row_count'],
                           'col_count': item['col_count'],
                           'fill_rate': item['fill_rate']})

    idx = 0
    for m in merged:
        idx += 1
        pages = m['pages']
        page_label = ('第%d页' % pages[0]) if len(pages) == 1 \
            else ('第%d-%d页' % (pages[0], pages[-1]))
        tables.append({
            'table_name': '%s-表格%d' % (page_label, idx),
            'source': 'PDF %s第%d个表格' % (
                ('第%d页 ' % pages[0]) if len(pages) == 1
                else ('第%d-%d页 ' % (pages[0], pages[-1])), idx),
            'rows': m['rows'],
            'merges': m['merges'],
            'row_count': m['row_count'],
            'col_count': m['col_count'],
            'fill_rate': m['fill_rate'],
        })
    return tables


def extract_tables(filepath, filename):
    """按扩展名分发，返回结构化表格列表。"""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext == 'docx':
        return extract_from_docx(filepath)
    if ext in ('xlsx', 'xlsm'):
        return extract_from_xlsx(filepath)
    if ext == 'pdf':
        return extract_from_pdf(filepath, filename)
    return []


def tables_to_text(tables):
    """把结构化表格转成可读文本，供向量检索使用（保留行列语义）。

    字段用 .get() 容错：审核入库时可能只有 table_name/rows，
    行列数与来源可从 rows 现算，缺字段不应让整个入库流程失败。
    """
    parts = []
    for t in tables:
        rows = t.get('rows') or []
        row_count = t.get('row_count') or len(rows)
        col_count = t.get('col_count') or (max((len(r) for r in rows), default=0))
        lines = ['【表格：%s（%d行×%d列，来源：%s）】'
                 % (t.get('table_name') or '表格', row_count, col_count,
                    t.get('source') or '')]
        for row in rows:
            lines.append(' | '.join('' if c is None else str(c) for c in row))
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
            c = ('' if cell is None else str(cell)).strip()
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


# ---- 卡片持久化标记（刷新后还原下载卡片用） ----
import base64
import json as _json

_CARD_RE = re.compile(r'\[\[KB_TABLE_CARD:([A-Za-z0-9+/=]+)\]\]')


def embed_card_marker(content, card):
    """把表格卡片信息编码成标记，追加到消息正文里一起存库。

    用 base64 避免 JSON 里的特殊字符破坏标记结构；前端 atob 解码还原。
    """
    if not card:
        return content
    payload = base64.b64encode(
        _json.dumps(card, ensure_ascii=False).encode('utf-8')).decode('ascii')
    return (content or '') + '\n\n[[KB_TABLE_CARD:%s]]' % payload


def strip_card_marker(content):
    """从消息正文里去掉标记，返回（纯文本, 卡片字典或 None）。"""
    text = content or ''
    m = _CARD_RE.search(text)
    if not m:
        return text, None
    card = None
    try:
        card = _json.loads(base64.b64decode(m.group(1)).decode('utf-8'))
    except Exception:
        pass
    return text.replace(m.group(0), '').rstrip(), card


def table_hit_payload(table, base_url='/api/v1'):
    """构造给前端的表格命中提示（只含真实文件的下载链接）。"""
    tid = table.get('id') if isinstance(table, dict) else table.id
    name = table.get('table_name', '') if isinstance(table, dict) else table.table_name
    doc = table.get('doc_name', '') if isinstance(table, dict) else table.doc_name
    kb_id = table.get('kb_id', '') if isinstance(table, dict) else table.kb_id
    # 默认名"表格 N"对用户无意义，改用文档名作为卡片标题
    if re.match(r'^表格\s*\d+$', name or '') and doc:
        name = re.sub(r'\.[^.]+$', '', doc)
    # URL 带 doc 参数：文档重新上传、表格 id 变化时后端可按文档名回退到最新原件
    from urllib.parse import quote
    url = '%s/kb/%s/tables/%s/download' % (base_url, kb_id, tid)
    if doc:
        url += '?doc=' + quote(doc, safe='')
    return {
        '__table_card__': {
            'table_id': tid,
            'table_name': name,
            'doc_name': doc,
            'url': url,
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
