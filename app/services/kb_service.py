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
CHUNK_OVERLAP = 60    # 相邻块重叠字符数
MAX_CONTEXT_CHARS = 6000  # 注入 prompt 的最大资料长度


def split_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """把文本切分为适合检索的块：优先按空行分段，再按长度切分"""
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    chunks = []
    buf = ''
    for para in paragraphs:
        # 单段过长时按字符切分
        while len(para) > chunk_size:
            if buf:
                chunks.append(buf)
                buf = ''
            chunks.append(para[:chunk_size])
            para = para[chunk_size - overlap:]
        if len(buf) + len(para) + 1 > chunk_size and buf:
            chunks.append(buf)
            buf = para
        else:
            buf = (buf + '\n' + para).strip() if buf else para
    if buf:
        chunks.append(buf)
    return chunks or [text[:chunk_size]]


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
    chunks = split_text(doc.content)
    created = []
    for i, content in enumerate(chunks):
        chunk = KBChunk(
            kb_id=doc.kb_id, doc_id=doc.id, doc_name=doc.filename,
            content=content, position=i,
        )
        db_add(chunk)
        created.append(chunk)
    doc.chunk_count = len(chunks)
    commit()

    # 写入向量库（整库重建，保证与文本块一致）
    if with_vectors:
        try:
            from app.services import kb_vector_service as vs
            vs.rebuild_index(doc.kb_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning('[KB] 向量索引失败，使用关键词检索兜底: %s', e)
    return len(chunks)


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


def build_context(kb_id, query, max_chars=MAX_CONTEXT_CHARS):
    """构造注入 system prompt 的知识库参考资料文本
    优先使用 Milvus 向量检索，失败时回退到 BM25 关键词检索
    """
    parts = []
    total = 0

    # 1) 向量检索
    try:
        from app.services import kb_vector_service as vs
        vector_results = vs.search(kb_id, query)
    except Exception:
        vector_results = None

    if vector_results:
        for doc_name, position, content, score in vector_results:
            header = '【资料：%s · 第%d段】' % (doc_name, position + 1)
            block = header + '\n' + content
            if total + len(block) > max_chars:
                break
            parts.append(block)
            total += len(block)

    # 2) 关键词兜底（向量无结果时）
    if not parts:
        for chunk, _ in retrieve(kb_id, query):
            header = '【资料：%s · 第%d段】' % (chunk.doc_name, chunk.position + 1)
            block = header + '\n' + chunk.content
            if total + len(block) > max_chars:
                break
            parts.append(block)
            total += len(block)

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
