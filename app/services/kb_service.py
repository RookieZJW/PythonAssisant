# -*- coding: utf-8 -*-
"""
知识库检索服务
==============
实现轻量级的文本检索（无需向量数据库）：
  1. 文档上传时按段落/字符数切分为文本块（chunk）
  2. 提问时对中文做 2-gram、英文/数字做单词切分，构建词频
  3. 用 TF-IDF 风格打分计算每个文本块与问题的相关性
  4. 取 top-k 文本块注入 system prompt，供大模型基于资料回答

设计取舍：不引入 embedding 模型或向量库，保持零新增依赖、部署简单。
对于个人知识库规模（数十份文档）足够实用。
"""
import re
import math
from collections import Counter

from app.models.knowledge_base import KBDocument, KBChunk

CHUNK_SIZE = 500      # 每块目标字符数
CHUNK_OVERLAP = 60    # 相邻块重叠字符数（仅作兜底，优先按句重叠）
MAX_CONTEXT_CHARS = 6000  # 注入 prompt 的最大资料长度

# 句子终止标点：切块只在这些标点后断开，保证句子完整
_SENTENCE_END = '。！？；!?;'
_CLAUSE_END = '，,、：:'  # 次优断点：句内逗号，长句无处可断时用


def _split_sentences(paragraph):
    """把一个段落拆成完整句子列表（标点保留在句尾）。"""
    sentences, buf = [], ''
    for ch in paragraph:
        buf += ch
        if ch in _SENTENCE_END:
            s = buf.strip()
            if s:
                sentences.append(s)
            buf = ''
    if buf.strip():
        sentences.append(buf.strip())
    return sentences or ([paragraph.strip()] if paragraph.strip() else [])


def _split_long_sentence(sentence, chunk_size):
    """极端超长的单句：先在子句标点处断，仍超长才按字符切（最后手段）。"""
    parts, buf = [], ''
    for ch in sentence:
        buf += ch
        if ch in _CLAUSE_END and len(buf) >= chunk_size * 0.6:
            parts.append(buf.strip())
            buf = ''
    if buf.strip():
        parts.append(buf.strip())
    result = []
    for part in parts:
        while len(part) > chunk_size:
            result.append(part[:chunk_size])
            part = part[chunk_size:]
        if part:
            result.append(part)
    return result or [sentence[:chunk_size]]


def split_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """语义感知切块：按段落聚合、按句子断开，绝不拦腰砍句子。

    策略：
      1. 段落是最小不可分割单元（空行分隔），短段落可合并到同一块；
      2. 段落超长时按句号/问号/叹号等句子边界切，句子保持完整；
      3. 单句极端超长时先按逗号断，最后才按字符切；
      4. 块间重叠取整句（最多 overlap 字符），不出现半句重复。
    """
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    if not paragraphs:
        return [text[:chunk_size]]

    # 先把每段拆成句子，超长句再细分
    units = []  # [(text, is_paragraph_start), ...]
    for pi, para in enumerate(paragraphs):
        sentences = _split_sentences(para)
        expanded = []
        for s in sentences:
            if len(s) > chunk_size:
                expanded.extend(_split_long_sentence(s, chunk_size))
            else:
                expanded.append(s)
        if expanded:
            units.append((expanded, pi))

    chunks, buf_parts = [], []

    def flush():
        if buf_parts:
            chunks.append('\n'.join(buf_parts).strip())
            buf_parts.clear()

    for sentences, pi in units:
        para_text = '\n'.join(sentences)
        # 单段就能塞进一块：作为整体，不拆
        if len(para_text) <= chunk_size:
            if buf_parts and len('\n'.join(buf_parts)) + len(para_text) + 1 > chunk_size:
                flush()
            buf_parts.append(para_text)
            continue
        # 超长段落：先结算已有缓冲，再按句子逐句装块
        flush()
        cur = ''
        for s in sentences:
            if cur and len(cur) + len(s) + 1 > chunk_size:
                chunks.append(cur)
                # 重叠：取上一块末尾的整句（不超过 overlap）
                tail = ''
                for prev in reversed(cur.split('\n')):
                    if len(tail) + len(prev) + 1 > overlap:
                        break
                    tail = (prev + '\n' + tail) if tail else prev
                cur = (tail + '\n' + s).strip() if tail else s
            else:
                cur = (cur + '\n' + s).strip() if cur else s
        if cur:
            chunks.append(cur)
    flush()
    return chunks or [text[:chunk_size]]


# ---------------- 结构化切分（制度/规章类文档） ----------------
# 中文标题：第X章 / 第X条 / 一、 / （一）
# 注意：阿拉伯数字编号（2.1 / 4.1.5）不在这里识别，
# 由 _classify_numbered() 区分「真标题」和「自带正文的编号条款」。
_HEAD_PATTERNS = [
    (re.compile(r'^第[一二三四五六七八九十百千零〇\d]+\s*[章节篇部]\s*\S{0,40}$'), 1),
    (re.compile(r'^第[一二三四五六七八九十百千零〇\d]+\s*条\s*\S{0,60}$'), 2),
    (re.compile(r'^[一二三四五六七八九十百]+\s*[、．.]\s*\S{0,60}$'), 2),
    (re.compile(r'^[（(][一二三四五六七八九十百\d]+[)）]\s*\S{0,60}$'), 4),
]

# 编号行：2 / 2.1 / 4.1.5.1 等，编号后允许直接跟中文或空格
_NUM_LINE = re.compile(r'^(\d+(?:\.\d+){0,5})[\s、.．]*(.*)$')
_SENT_END_CHARS = '。！？；!?;'
MIN_CHUNK_SIZE = 120  # 小于此长度的块并入相邻块，避免碎块


def _match_heading(line):
    """返回 (level, 标题文本)；不是标题返回 None。"""
    s = line.strip()
    if not s or len(s) > 90:
        return None
    for pattern, level in _HEAD_PATTERNS:
        if pattern.match(s):
            return level, s
    return None


def _classify_numbered(line):
    """识别阿拉伯数字编号行，区分「标题」与「自带正文的条款」。

    中文制度文档里两种写法都很常见：
      「2职责与权限」「4.1危险废物的收集和包装」→ 真标题（短、无句末标点）
      「2.1.1负责组织编制…。」→ 条款正文（带句号），不能当成标题单独成块

    返回 (kind, level, num, rest) 或 None。
    """
    s = line.strip()
    m = _NUM_LINE.match(s)
    if not m:
        return None
    num, rest = m.group(1), m.group(2).strip()
    # 化学式/型号（如 6-氨基-2,2,7-三氟…）不是章节编号：
    # 编号后必须以中文或字母开头，排除 - 、 ， 等符号
    if rest and not re.match(r'^[\u4e00-\u9fffA-Za-z]', rest):
        return None
    level = num.count('.') + 1
    if not rest:
        return 'heading', level, num, ''
    # 真标题都很短（「职责与权限」「废物分类」「对外转运」）。
    # PDF 折行会把长条款的第一行断在半个词上（如「…按照要求的位置、层」），
    # 这行结尾虽无句号，但远超过 20 字，必须判为条款，否则开头会被当标题吞掉。
    is_heading = (rest[-1] not in _SENT_END_CHARS and len(rest) <= 20)
    return ('heading' if is_heading else 'clause'), level, num, rest


def _drop_repeated_headers(lines):
    """过滤跨页重复的页眉/页脚行，保留第一次出现（元数据不丢）。

    PDF 每页都会重复「公司名 / 文件编号 / 第X页共Y页」，这些行混进正文
    会污染切块与检索。按归一化后的行文本计数，出现 >=2 次视为页眉。
    """
    from collections import Counter
    def key(s):
        return re.sub(r'第\s*\d+\s*页\s*共\s*\d+\s*页', '第X页共Y页', s)
    cnt = Counter(key(ln.strip()) for ln in lines if len(ln.strip()) >= 8)
    repeated = {k for k, n in cnt.items() if n >= 2}
    if not repeated:
        return lines
    seen, out = set(), []
    # 只切「典型页眉片段」粘在行尾的情况：公司名、文档标题、文件编号等。
    # 不能把所有重复行都当页眉——「公司废包装袋分类」这类正文小标题也会重复，
    # 误切会把标题和正文粘成一行。
    _HEADER_HINT = ('公司', '有限公司', '管理制度', '操作规程', '文件编号', '生效日期', '版', '共')
    sticky = sorted(
        (h for h in repeated if len(h) >= 4 and any(k in h for k in _HEADER_HINT)),
        key=len, reverse=True)
    for ln in lines:
        k = key(ln.strip())
        if k in repeated:
            if k in seen:
                continue
            seen.add(k)
        # 页眉粘在正文行尾（PDF 文本层常见）：切掉重复片段，保留正文
        stripped = ln.strip()
        for hdr in sticky:
            if stripped.endswith(hdr) and stripped != hdr:
                ln = ln[:len(ln.rstrip()) - len(hdr)].rstrip()
                break
        out.append(ln)
    return out


# 行尾是这些标点时，几乎可以确定是同一段被 PDF 折行（软换行）
_SOFT_TAIL = '，,、：:；;（(【「"\'' + '、'
# 句子真正结束的标点：遇到就换行（硬换行）
_HARD_TAIL = '。！？!?'
# 行首是这些闭合标点时，说明承接上一行
_SOFT_HEAD = '，,、。）】》」\'\'"%'


def _is_soft_break(prev_line, cur_line):
    """判断两行之间是 PDF 折行（应接回同一段）还是真段落边界。"""
    p, c = prev_line[-1], cur_line[0]
    # 上一行本身就是标题/编号标题 → 一般不接下一行（否则标题被吞、章节路径错乱）
    prev_info = _classify_numbered(prev_line)
    if _match_heading(prev_line) or (prev_info and prev_info[0] == 'heading'):
        # 例外：短标题被 PDF 折行（如「4.3 危险废物的对外转」+「运」）。
        # 下一行只有 1~4 个字且不含标点时，判定为标题的续行，接回去。
        if len(cur_line) <= 4 and not any(ch in '。，、；：,.!?;:' for ch in cur_line):
            return True
        return False
    # 下一行是标题或编号条款 → 真边界，不合并
    if _match_heading(cur_line) or _classify_numbered(cur_line):
        return False
    # 上一行句子已完整结束 → 真边界，不合并
    if p in _HARD_TAIL:
        return False
    # 上一行以连接标点结尾 / 下一行以闭合标点开头 → 明显是折行
    if p in _SOFT_TAIL or c in _SOFT_HEAD:
        return True
    # 中文排版默认：上一行没有句号结尾就视为同段折行
    # （PDF 按视觉宽度断行，不会在意语义完整性）
    return True


def _unwrap_soft_lines(lines):
    """把 PDF 因页面宽度折行而拆开的段落接回一行。

    只对「软换行」做拼接（中文之间不加空格）；标题、编号条款、句子
    完整结束处仍保留换行，切块器据此识别段落边界。
    """
    out = []
    for raw in lines:
        s = raw.strip()
        if not s:
            if out and out[-1] != '':
                out.append('')
            continue
        if out and out[-1] and _is_soft_break(out[-1], s):
            out[-1] = out[-1] + s
        else:
            out.append(s)
    return out


def _drop_repeated_headers_tagged(tagged):
    """_drop_repeated_headers 的带页码版本：[(text, page)] 原样过滤。"""
    if not tagged:
        return tagged
    from collections import Counter
    def key(s):
        return re.sub(r'第\s*\d+\s*页\s*共\s*\d+\s*页', '第X页共Y页', s)
    texts = [t for t, _ in tagged]
    cnt = Counter(key(t.strip()) for t in texts if len(t.strip()) >= 8)
    repeated = {k for k, n in cnt.items() if n >= 2}
    if not repeated:
        return tagged
    _HEADER_HINT = ('公司', '有限公司', '管理制度', '操作规程', '文件编号', '生效日期', '版', '共')
    sticky = sorted((h for h in repeated if len(h) >= 4 and any(k in h for k in _HEADER_HINT)),
                    key=len, reverse=True)
    seen, out = set(), []
    for text, page in tagged:
        k = key(text.strip())
        if k in repeated:
            if k in seen:
                continue
            seen.add(k)
        stripped = text.strip()
        for hdr in sticky:
            if stripped.endswith(hdr) and stripped != hdr:
                text = text[:len(text.rstrip()) - len(hdr)].rstrip()
                break
        out.append((text, page))
    return out


def _unwrap_soft_lines_tagged(tagged):
    """_unwrap_soft_lines 的带页码版本：合并行时取来源行的最大页码。"""
    out = []   # [(text, page)]
    for raw, page in tagged:
        s = raw.strip()
        if not s:
            if out and out[-1][0] != '':
                out.append(('', page))
            continue
        if out and out[-1][0] and _is_soft_break(out[-1][0], s):
            prev_text, prev_page = out[-1]
            out[-1] = (prev_text + s, max(prev_page, page))
        else:
            out.append((s, page))
    return out


_PAGE_MARK_RE = re.compile(r'^\[\[PDF_PAGE:(\d+)\]\]$')


def split_structured(text, chunk_size=CHUNK_SIZE, with_page=False):
    """按文档结构切块，每块带章节路径；可选返回页码。

    改进点（解决制度类 PDF 被切成一堆十来字碎块的问题）：
      1. 区分「编号标题」与「编号条款」：
         「2职责与权限」是标题；「2.1.1负责……。」是自带正文的条款，
         不再把每个编号行当成独立标题切出 10~30 字的小块。
      2. 同一父章节下的相邻条款聚合成块，直到接近 chunk_size；
         不足 MIN_CHUNK_SIZE 的尾块并入上一块，避免碎块。
      3. 跨页重复的页眉/页脚只保留第一次，避免污染正文。
      4. 真·超长段落（如无编号的长段说明）仍按句子边界切，句子不拦腰断。
      5. 章节标题（如「1 目的」）写入正文首行，而不只是放进 section_path。
      6. 识别 [[PDF_PAGE:N]] 标记，记录每块结束页码（with_page=True 时返回）。

    返回：
      with_page=False → [(section_path, content), ...]（兼容旧调用）
      with_page=True  → [(section_path, content, page), ...]，page 为 0 表示无页码
    """
    if not text:
        return []
    # 先把 PDF 页标记从各行剥离并记住页码。必须在软换行合并之前做，
    # 否则页标记会被当成正文行粘进段落。
    raw_lines = text.split('\n')
    tagged = []         # [(text, page)]
    current_page = 0
    for raw in raw_lines:
        pm = _PAGE_MARK_RE.match(raw.strip())
        if pm:
            current_page = int(pm.group(1))
            continue
        tagged.append((raw, current_page))

    plain_lines = [x[0] for x in tagged]

    # 探测是否存在结构标题（中文标题 或 编号标题）
    has_structure = any(
        _match_heading(ln) or
        (lambda info: info and info[0] == 'heading')(_classify_numbered(ln))
        for ln in plain_lines
    )
    if not has_structure:
        # 回退分支同样要用剥离页标记后的文本，否则 [[PDF_PAGE:N]] 会漏进正文
        clean = '\n'.join(plain_lines)
        pieces = split_text(clean, chunk_size)
        return [( '', c, 0) for c in pieces] if with_page else [('', c) for c in pieces]

    # 页眉过滤 + 软换行合并，页码随行一起走（合并时取来源行的最大页码）
    tagged = _drop_repeated_headers_tagged(tagged)
    lines = _unwrap_soft_lines_tagged(tagged)

    sections = []   # [(path, [(content_line, page), ...])]
    stack = []      # [(level, title)]
    buf = []        # [(line, page)]

    def flush_section():
        real = [x for x in buf if x[0].strip()]
        if real:
            path = ' > '.join(t for _, t in stack)
            sections.append((path, real))
        buf.clear()

    for raw, curpage in lines:
        s = raw.strip()
        if not s:
            continue
        numbered = _classify_numbered(s)
        chinese = _match_heading(s) if not numbered else None

        if numbered and numbered[0] == 'heading':
            flush_section()
            _, level, num, rest = numbered
            title = (num + ' ' + rest).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            # 标题写进正文首行（用户要求：标题应在文本块中可见）
            buf.append((title, curpage))
        elif chinese:
            flush_section()
            level, title = chinese
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            buf.append((title, curpage))
        elif numbered and numbered[0] == 'clause':
            _, level, num, rest = numbered
            buf.append(((num + ' ' + rest).strip(), curpage))
        else:
            buf.append((s, curpage))
    flush_section()

    # 按节聚合：条款逐条累计，接近目标大小才切块；过小的尾块并入上一块
    result = []     # [(path, body, end_page)]
    for path, body_lines in sections:
        cur, cur_len, cur_page = [], 0, 0
        for line_text, page in body_lines:
            if cur and cur_len + len(line_text) > chunk_size:
                result.append((path, '\n'.join(cur), cur_page))
                cur, cur_len, cur_page = [], 0, 0
            cur.append(line_text)
            cur_len += len(line_text)
            if page:
                cur_page = page
        if cur:
            body = '\n'.join(cur)
            # 每节（标题+正文）独立成块，不再并入上一块：
            # 并入会把短节的正文串进别的章节，破坏 section_path 语义和检索隔离。
            # 标题已写进正文，短节虽小但语义完整。
            result.append((path, body, cur_page))

    # 真·超长单块（如无编号的连续长段落）才按句子边界再切，
    # 且每片保留同一 section_path，供父子块聚合
    expanded = []   # [(path, body, page)]
    for path, body, page in result:
        if len(body) > chunk_size * 2:
            for piece in split_text(body, chunk_size):
                expanded.append((path, piece, page))
        else:
            expanded.append((path, body, page))

    # 只有标题、没有正文的碎块（如「第一章 危险废物管理」10 字）：
    # 标题要写进正文，但不能自己单独成块——并入下一个块的开头。
    final = []
    pending_title = None
    for i, (path, body, page) in enumerate(expanded):
        title = path.split(' > ')[-1].strip() if path else ''
        is_title_only = (title and body.strip() == title)
        if is_title_only:
            if pending_title:
                # 连续多个空标题节：都留着，接到下个有正文的块
                pending_title += '\n' + body
            else:
                pending_title = body
            continue
        if pending_title:
            body = pending_title + '\n' + body
            pending_title = None
        final.append((path, body, page))
    # 末尾仍有悬空标题 → 作为独立块保留（至少不丢标题）
    if pending_title:
        last_path = expanded[-1][0] if expanded else ''
        last_page = expanded[-1][2] if expanded else 0
        final.append((last_path, pending_title, last_page))

    if with_page:
        return final
    return [(path, body) for path, body, _ in final]


def tokenize(text):
    """中英文混合分词：中文 2-gram，英文/数字按单词"""
    if not text:
        return []
    text = text.lower()
    tokens = []
    # 英文与数字
    for m in re.findall(r'[a-z0-9]+', text):
        if len(m) >= 2:
            tokens.append(m)
    # 中文 2-gram（保留单字以提升短查询命中）
    cn = re.findall(r'[\u4e00-\u9fff]+', text)
    for seg in cn:
        if len(seg) == 1:
            tokens.append(seg)
        else:
            for i in range(len(seg) - 1):
                tokens.append(seg[i:i+2])
    return tokens


def index_document(doc, with_vectors=True):
    """为文档建立索引：切块入库 + 写入 Milvus 向量（失败时保留文本块供 BM25 兜底）

    with_vectors=False 用于批量上传：先只切块入库，整批处理完再统一重建一次向量，
    避免每上传一个文件就跑一遍全库 embedding。
    """
    KBChunk.query.filter_by(doc_id=doc.id).delete()
    structured = split_structured(doc.content)
    created = []
    for i, (section_path, content) in enumerate(structured):
        chunk = KBChunk(
            kb_id=doc.kb_id, doc_id=doc.id, doc_name=doc.filename,
            content=content, position=i, section_path=section_path,
        )
        db_add(chunk)
        created.append(chunk)
    doc.chunk_count = len(structured)
    commit()

    # 写入向量库（整库重建，保证与文本块一致）
    if with_vectors:
        try:
            from app.services import kb_vector_service as vs
            vs.rebuild_index(doc.kb_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning('[KB] 向量索引失败，使用关键词检索兜底: %s', e)
    return len(structured)


def _db():
    from app.extensions import db
    return db


def db_add(obj):
    _db().session.add(obj)


def commit():
    _db().session.commit()


def retrieve(kb_id, query, top_k=4):
    """检索与问题最相关的文本块，返回 [(chunk, score), ...]"""
    chunks = KBChunk.query.filter_by(kb_id=kb_id).all()
    if not chunks:
        return []
    q_tokens = tokenize(query)
    if not q_tokens:
        return []
    q_tf = Counter(q_tokens)

    # 文档频率（DF）：用于计算 IDF
    df = Counter()
    chunk_tokens = []
    for chunk in chunks:
        toks = tokenize(chunk.content)
        chunk_tokens.append(set(toks))
        for t in set(toks):
            df[t] += 1

    n = len(chunks)
    scored = []
    for i, chunk in enumerate(chunks):
        toks = tokenize(chunk.content)
        tf = Counter(toks)
        score = 0.0
        for term, qfreq in q_tf.items():
            if term not in tf:
                continue
            idf = math.log((n + 1) / (df.get(term, 0) + 1)) + 1
            score += qfreq * tf[term] * idf
        if score > 0:
            # 文档名命中给予轻微加权
            if any(t in chunk.doc_name.lower() for t in q_tokens):
                score *= 1.15
            scored.append((chunk, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def _expand_to_section(kb_id, doc_name, position, hit_content, seen_sections):
    """把命中的细块扩展为完整章节。

    返回 (header, 完整正文)。若该块无 section_path 或聚合失败，回退到单块。
    """
    # 按 doc_name + position 精确定位命中的块
    chunk = KBChunk.query.filter_by(
        kb_id=kb_id, doc_name=doc_name, position=position).first()
    if not chunk or not getattr(chunk, 'section_path', ''):
        return '【资料：%s · 第%d段】' % (doc_name, position + 1), hit_content

    section = chunk.section_path
    key = (doc_name, section)
    if key in seen_sections:
        return None, None  # 同节已返回，避免重复
    seen_sections.add(key)

    # 取同文档、同章节路径的全部块，按 position 还原原文顺序
    siblings = KBChunk.query.filter_by(
        kb_id=kb_id, doc_id=chunk.doc_id, section_path=section
    ).order_by(KBChunk.position).all()
    body = '\n'.join(c.content for c in siblings if c.content).strip()
    return '【资料：%s · %s】' % (doc_name, section), (body or hit_content)


def build_context(kb_id, query, max_chars=MAX_CONTEXT_CHARS):
    """构造注入 system prompt 的知识库参考资料文本
    优先使用 Milvus 向量检索，失败时回退到 BM25 关键词检索
    """
    parts = []
    total = 0
    seen_sections = set()  # 已返回的章节，去重

    def add_block(doc_name, position, content):
        nonlocal total
        header, body = _expand_to_section(
            kb_id, doc_name, position, content, seen_sections)
        if header is None:
            return False
        block = header + '\n' + body
        if total + len(block) > max_chars and parts:
            return False
        parts.append(block)
        total += len(block)
        return True

    # 1) 向量检索
    try:
        from app.services import kb_vector_service as vs
        vector_results = vs.search(kb_id, query)
    except Exception:
        vector_results = None

    if vector_results:
        for doc_name, position, content, score in vector_results:
            add_block(doc_name, position, content)

    # 2) 关键词兜底（向量无结果时）
    if not parts:
        for chunk, _ in retrieve(kb_id, query):
            add_block(chunk.doc_name, chunk.position, chunk.content)

    return '\n\n---\n\n'.join(parts) if parts else None


def kb_system_prompt(kb_name, context, base_prompt=None):
    """把知识库资料包装成 system prompt"""
    instructions = (
        '你正在使用知识库「%s」回答用户问题。\n'
        '请严格依据下面提供的【参考资料】作答；如果资料中没有相关信息，'
        '请明确说明"知识库中没有相关内容"，不要编造。'
        '回答时尽量引用资料中的具体内容，保持简洁准确。\n\n'
        '===== 参考资料 =====\n%s\n===== 参考资料结束 ====='
    ) % (kb_name, context)
    if base_prompt:
        instructions = base_prompt + '\n\n' + instructions
    return instructions
