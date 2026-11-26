# -*- coding: utf-8 -*-
"""
知识库向量检索服务（Milvus + 通义千问 Embedding）
==================================================
- 向量库：Milvus（本机 localhost:19530），每个知识库一个 collection
- Embedding：通义千问 text-embedding-v3（1024 维）
- 降级：embedding 不可用时回退到 BM25 关键词检索（kb_service.retrieve）

Milvus collection 设计：
  collection 名 = kb_<知识库ID的短哈希>，避免非法字符
  字段：id(主键) / kb_id / doc_id / doc_name / content / position / vector(1024)
"""
import re
import hashlib
import logging
import time

logger = logging.getLogger(__name__)

MILVUS_URI = 'http://localhost:19530'
EMBED_MODEL = 'text-embedding-v3'
DIM = 1024
TOP_K = 5
EMBED_BATCH = 10   # DashScope text-embedding-v3 单次最多 10 条
MAX_QUERY_LIMIT = 16384  # Milvus query 的 offset+limit 上限

_client = None
_last_client_attempt = 0.0
CLIENT_RETRY_INTERVAL = 5.0  # 连接失败后最快 5 秒重试，不再"一次失败终身降级"


def get_client():
    """获取 Milvus 客户端（单例缓存 + 失败后节流重试）

    服务可能早于 Milvus（WSL）启动，此时首次连接必然失败。旧实现会把
    _client_failed 永久置 True，导致 Milvus 起来后仍一直走关键词检索。
    这里改为带节流间隔的自动重试，Milvus 就绪后即可自行恢复。
    """
    global _client, _last_client_attempt
    if _client is not None:
        return _client
    now = time.monotonic()
    if now - _last_client_attempt < CLIENT_RETRY_INTERVAL:
        return None
    _last_client_attempt = now
    try:
        from pymilvus import MilvusClient
        _client = MilvusClient(uri=MILVUS_URI)
        logger.info('[KB向量] Milvus 客户端已就绪')
        return _client
    except Exception as e:
        logger.warning('[KB向量] Milvus 连接失败（%.0f 秒后重试）: %s',
                       CLIENT_RETRY_INTERVAL, e)
        return None


def _reset_client():
    """操作异常时丢弃缓存的客户端，使下一次调用能重建连接。"""
    global _client, _last_client_attempt
    if _client is not None:
        logger.warning('[KB向量] 丢弃失效的 Milvus 客户端，将在下次调用时重连')
    _client = None
    _last_client_attempt = 0.0


def collection_name(kb_id):
    """把知识库ID映射为合法的 collection 名"""
    h = hashlib.md5(kb_id.encode()).hexdigest()[:12]
    return 'kb_' + h


def embed(texts):
    """调用通义千问生成 embedding，返回向量列表；失败返回 None"""
    try:
        import os
        from dotenv import load_dotenv
        from dashscope import TextEmbedding
        load_dotenv()
        key = os.getenv('QWEN_API_KEY')
        if not key:
            return None
        # DashScope text-embedding-v3 单次最多 10 条，分批
        result = []
        for i in range(0, len(texts), 10):
            batch = texts[i:i+10]
            resp = TextEmbedding.call(model=EMBED_MODEL, input=batch, api_key=key)
            if resp.status_code != 200:
                logger.warning('[KB向量] embedding 失败: %s', resp.message)
                return None
            for item in resp.output['embeddings']:
                result.append(item['embedding'])
        return result
    except Exception as e:
        logger.warning('[KB向量] embedding 异常: %s', e)
        return None


def ensure_collection(kb_id):
    """确保知识库对应的 collection 存在（显式 schema，兼容 Milvus 2.x）"""
    client = get_client()
    if not client:
        return None
    name = collection_name(kb_id)
    try:
        if not client.has_collection(collection_name=name):
            from pymilvus import DataType, CollectionSchema, FieldSchema
            fields = [
                FieldSchema(name='id', dtype=DataType.VARCHAR, is_primary=True, max_length=64),
                FieldSchema(name='kb_id', dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name='doc_id', dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name='doc_name', dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name='content', dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name='position', dtype=DataType.INT64),
                FieldSchema(name='vector', dtype=DataType.FLOAT_VECTOR, dim=DIM),
            ]
            schema = CollectionSchema(fields=fields, description='Knowledge base chunks')
            from pymilvus.milvus_client.index import IndexParams
            index_params = IndexParams()
            index_params.add_index(field_name='vector', index_type='AUTOINDEX',
                                   metric_type='COSINE')
            client.create_collection(collection_name=name, schema=schema,
                                     index_params=index_params)
            logger.info('[KB向量] 已创建集合 %s', name)
        return name
    except Exception as e:
        logger.warning('[KB向量] 创建集合失败: %s', e)
        _reset_client()
        return None


def index_chunks(kb_id, chunks):
    """把文本块写入向量库。chunks: [{id, doc_id, doc_name, content, position}]"""
    name = ensure_collection(kb_id)
    if not name:
        return False
    vectors = embed([c['content'] for c in chunks])
    if not vectors or len(vectors) != len(chunks):
        return False
    client = get_client()
    try:
        # 先清理该知识库的旧向量（重建索引）
        # Milvus Lite/MilvusClient 用 query+delete
        old = client.query(collection_name=name, filter='kb_id != ""',
                           output_fields=['id'], limit=MAX_QUERY_LIMIT)
        if old:
            client.delete(collection_name=name, ids=[o['id'] for o in old])
        rows = []
        for c, v in zip(chunks, vectors):
            rows.append({
                'id': c['id'], 'kb_id': kb_id, 'doc_id': c['doc_id'],
                'doc_name': c['doc_name'], 'content': c['content'],
                'position': c['position'], 'vector': v,
            })
        client.insert(collection_name=name, data=rows)
        client.flush(collection_name=name)  # 确保立即可检索
        logger.info('[KB向量] 已写入 %d 条向量到 %s', len(rows), name)
        return True
    except Exception as e:
        logger.warning('[KB向量] 写入失败: %s', e)
        _reset_client()
        return False


def delete_document_vectors(kb_id, doc_id):
    """删除某文档的所有向量"""
    name = ensure_collection(kb_id)
    if not name:
        return
    client = get_client()
    try:
        rows = client.query(collection_name=name, filter='doc_id == "%s"' % doc_id,
                            output_fields=['id'], limit=MAX_QUERY_LIMIT)
        if rows:
            client.delete(collection_name=name, ids=[r['id'] for r in rows])
            client.flush(collection_name=name)  # 确保删除后立即可见
            logger.info('[KB向量] 已删除文档 %s 的 %d 条向量', doc_id, len(rows))
    except Exception as e:
        logger.warning('[KB向量] 删除文档向量失败: %s', e)
        _reset_client()


def delete_kb_collection(kb_id):
    """删除知识库的整个向量集合"""
    client = get_client()
    if not client:
        return
    name = collection_name(kb_id)
    try:
        if client.has_collection(collection_name=name):
            client.drop_collection(collection_name=name)
            logger.info('[KB向量] 已删除集合 %s', name)
    except Exception as e:
        logger.warning('[KB向量] 删除集合失败: %s', e)
        _reset_client()


def search(kb_id, query, top_k=TOP_K):
    """向量检索，返回 [(doc_name, position, content, score), ...]；失败返回 None"""
    name = ensure_collection(kb_id)
    if not name:
        return None
    client = get_client()
    try:
        cnt = client.get_collection_stats(collection_name=name).get('row_count', 0)
        if not cnt:
            return None
        vec = embed([query])
        if not vec:
            return None
        hits = client.search(
            collection_name=name,
            data=[vec[0]],
            limit=min(top_k, cnt),
            output_fields=['doc_name', 'position', 'content'],
        )
        results = []
        for hit in hits[0]:
            entity = hit.get('entity', {})
            results.append((entity.get('doc_name', ''), entity.get('position', 0),
                            entity.get('content', ''), hit.get('distance', 0)))
        return results
    except Exception as e:
        logger.warning('[KB向量] 检索失败: %s', e)
        _reset_client()
        return None


def rebuild_index(kb_id):
    """从数据库重建整个知识库的向量索引，返回是否成功"""
    ok = False
    for stage, done, total, msg in iter_rebuild_index(kb_id):
        if stage == 'stored':
            ok = True
        elif stage in ('embed_failed', 'no_collection', 'error'):
            logger.warning('[KB向量] 重建索引中断（%s）：%s', stage, msg or '')
            return False
    return ok


def iter_rebuild_index(kb_id, batch_size=EMBED_BATCH):
    """生成器版整库重建：每完成一批 embedding 就 yield 一次进度，供前端流式展示。

    yield (stage, done, total, message)
      stage:
        no_chunks      库里没有文本块，无需处理
        no_collection  向量库不可用
        progress       已完成 done/total 段的向量化
        embed_failed   embedding 调用失败（旧向量保持不变）
        stored         向量已写入并 flush
        error          写库异常
    """
    from app.models.knowledge_base import KBChunk

    chunks = KBChunk.query.filter_by(kb_id=kb_id).order_by(
        KBChunk.doc_id, KBChunk.position).all()
    total = len(chunks)
    if not total:
        yield ('no_chunks', 0, 0, None)
        return

    name = ensure_collection(kb_id)
    if not name:
        yield ('no_collection', 0, total, '向量库不可用')
        return
    client = get_client()
    if not client:
        yield ('no_collection', 0, total, '向量库连接失败')
        return

    # 先把向量全部算出来再动旧数据：embedding 失败时不会清空已有索引
    vectors = []
    for i in range(0, total, batch_size):
        part = chunks[i:i + batch_size]
        vecs = embed([c.content for c in part])
        if not vecs or len(vecs) != len(part):
            yield ('embed_failed', len(vectors), total, None)
            return
        vectors.extend(vecs)
        yield ('progress', len(vectors), total, None)

    try:
        old = client.query(collection_name=name, filter='kb_id != ""',
                           output_fields=['id'], limit=MAX_QUERY_LIMIT)
        if old:
            client.delete(collection_name=name, ids=[o['id'] for o in old])
        rows = []
        for c, v in zip(chunks, vectors):
            rows.append({
                'id': c.id, 'kb_id': kb_id, 'doc_id': c.doc_id,
                'doc_name': c.doc_name, 'content': c.content,
                'position': c.position, 'vector': v,
            })
        client.insert(collection_name=name, data=rows)
        client.flush(collection_name=name)
        logger.info('[KB向量] 已重建 %d 条向量到 %s', len(rows), name)
        yield ('stored', total, total, None)
    except Exception as e:
        logger.warning('[KB向量] 重建写入失败: %s', e)
        _reset_client()
        yield ('error', 0, total, str(e))

