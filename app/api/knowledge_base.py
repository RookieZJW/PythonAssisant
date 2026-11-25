# -*- coding: utf-8 -*-
"""
知识库 API
==========
提供多用户知识库的完整接口：
  - 知识库 CRUD（创建/列表/详情/删除）
  - 文档上传与删除
  - 分享管理（分享给指定用户/取消分享/查看分享列表）
  - 检索预览（可选，供前端调试）

所有接口都基于 session['user_id'] 做权限校验：
  - owner 才能修改知识库、上传/删除文档、管理分享
  - 被分享者只能查看和基于知识库提问
"""
import json
import logging
import os
import uuid
from flask import Blueprint, Response, request, session, stream_with_context
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase, KBDocument, KBShare
from app.services import kb_service
from app.utils.response import success, error
from app.extensions import db

kb_bp = Blueprint('knowledge_base', __name__)
logger = logging.getLogger(__name__)

ALLOWED = {'txt', 'md', 'pdf', 'docx', 'doc', 'py', 'js', 'html', 'css',
           'json', 'xml', 'csv', 'log', 'java', 'c', 'cpp', 'h'}
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_BULK_FILES = 20              # 单次批量上传最多文件数
MAX_FILE_BYTES = 5 * 1024 * 1024  # 单文件上限 5MB
MAX_CONTENT_CHARS = 500000        # 单文档正文上限 50 万字


def _sse(payload):
    """把字典序列化成一条 SSE 事件"""
    return 'data: ' + json.dumps(payload, ensure_ascii=False) + '\n\n'


def _cleanup_files(paths):
    """清理临时文件；失败不影响已经成功入库的数据"""
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception as e:
            logger.warning('[KB上传] 临时文件清理失败（不影响入库）：%s', e)


def _uid():
    return session.get('user_id', '')


def _require_login():
    uid = _uid()
    if not uid:
        return None, error("请先登录", 401)
    return uid, None


def _parse_file(filepath, filename):
    """复用 upload 模块的解析逻辑"""
    from app.api.upload import _parse_file as parse
    return parse(filepath, filename)


def _safe_filename(raw):
    """保留中文文件名的安全化处理（避免路径穿越和非法字符）"""
    name = os.path.basename((raw or '').replace('\\', '/')).strip()
    for ch in '<>:"|?*\r\n\t':
        name = name.replace(ch, '_')
    name = name.rstrip(' .')
    return name or 'unnamed'


# ---------- 知识库 CRUD ----------

@kb_bp.route('/kb', methods=['GET'])
def list_kb():
    _, err = _require_login()
    if err: return err
    return success(KnowledgeBase.list_for_user(_uid()))


@kb_bp.route('/kb', methods=['POST'])
def create_kb():
    uid, err = _require_login()
    if err: return err
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return error("知识库名称不能为空", 400)
    if len(name) > 120:
        return error("知识库名称不能超过120字", 400)
    exists = KnowledgeBase.query.filter_by(user_id=uid, name=name).first()
    if exists:
        return error("已有同名知识库", 409)
    kb = KnowledgeBase.create(name, (data.get('description') or '').strip(), uid)
    d = kb.to_dict()
    d['role'] = 'owner'
    return success(d, "知识库已创建")


@kb_bp.route('/kb/<kb_id>', methods=['GET'])
def get_kb(kb_id):
    uid, err = _require_login()
    if err: return err
    kb = KnowledgeBase.get_visible(kb_id, uid)
    if not kb:
        return error("知识库不存在或无访问权限", 404)
    data = kb.to_dict()
    data['role'] = 'owner' if kb.user_id == uid else 'shared'
    data['documents'] = [d.to_dict() for d in KBDocument.query.filter_by(kb_id=kb_id).order_by(KBDocument.created_at.desc()).all()]
    if kb.user_id == uid:
        data['shares'] = [s.to_dict() for s in KBShare.query.filter_by(kb_id=kb_id).all()]
    return success(data)


@kb_bp.route('/kb/<kb_id>', methods=['DELETE'])
def delete_kb(kb_id):
    uid, err = _require_login()
    if err: return err
    if not KnowledgeBase.is_owner(kb_id, uid):
        return error("只有知识库所有者可以删除", 403)
    kb = KnowledgeBase.query.get(kb_id)
    if not kb:
        return error("知识库不存在", 404)
    kb.delete_cascade()
    return success(None, "知识库已删除")


# ---------- 文档管理 ----------

@kb_bp.route('/kb/<kb_id>/documents', methods=['POST'])
def upload_document(kb_id):
    uid, err = _require_login()
    if err: return err
    if not KnowledgeBase.is_owner(kb_id, uid):
        return error("只有知识库所有者可以上传文档", 403)

    file = request.files.get('file')
    if not file or not file.filename:
        return error("请选择文件", 400)
    filename = _safe_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED:
        return error("不支持的文件格式", 400)

    # 同名文档去重：先删除旧文档及其块
    old = KBDocument.query.filter_by(kb_id=kb_id, filename=filename).first()
    if old:
        old.delete_cascade()

    tmp_path = os.path.join(UPLOAD_DIR, ('kb_' + filename))
    try:
        file.save(tmp_path)
        file_size = os.path.getsize(tmp_path)
        content = _parse_file(tmp_path, filename)
    finally:
        # 临时文件清理失败不能影响已经成功的解析结果
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception as e:
            logger.warning('[KB上传] 临时文件清理失败（不影响入库）：%s', e)

    if not content or content.startswith('['):
        return error("文档解析失败或内容为空：" + str(content)[:100], 400)
    if len(content) > 500000:
        return error("文档内容过长（上限50万字）", 400)

    doc = KBDocument(kb_id=kb_id, filename=filename, content=content,
                     size=file_size)
    # 文件大小需在删除前记录
    db.session.add(doc)
    db.session.commit()
    count = kb_service.index_document(doc)
    return success({'id': doc.id, 'filename': filename, 'chunk_count': count}, "文档已加入知识库")


@kb_bp.route('/kb/<kb_id>/documents/bulk', methods=['POST'])
def upload_documents_bulk(kb_id):
    """批量上传文档，用 SSE 把「解析 → 切块 → 向量化」的进度实时推给前端。

    请求: multipart/form-data，字段名 files（可多个）
    响应: text/event-stream，每条事件是一个 JSON：
      {"type":"start","total":3,"rejected":[...]}
      {"type":"file","stage":"parse|chunk|done|error","index":1,"total":3,
       "filename":"a.pdf","message":"...","chunk_count":7}
      {"type":"vector","stage":"start|progress|done|warn","done":30,"total":59,"message":"..."}
      {"type":"end","success":2,"failed":1,"chunks":41,"vector_ok":true,"vector_msg":""}
    """
    uid, err = _require_login()
    if err: return err
    if not KnowledgeBase.is_owner(kb_id, uid):
        return error("只有知识库所有者可以上传文档", 403)

    incoming = [f for f in request.files.getlist('files') if f and f.filename]
    if not incoming:
        incoming = [f for f in request.files.getlist('file') if f and f.filename]
    if not incoming:
        return error("请选择文件", 400)

    # 先把文件落盘，避免流式过程中 request 上下文退出后拿不到文件
    staged, rejected = [], []
    for f in incoming[:MAX_BULK_FILES]:
        filename = _safe_filename(f.filename)
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in ALLOWED:
            rejected.append({'filename': filename, 'reason': '不支持的文件格式'})
            continue
        tmp_path = os.path.join(
            UPLOAD_DIR, 'bulk_%s_%s' % (uuid.uuid4().hex[:10], filename))
        try:
            f.save(tmp_path)
            size = os.path.getsize(tmp_path)
        except Exception as e:
            logger.warning('[KB批量] 文件保存失败 %s: %s', filename, e)
            rejected.append({'filename': filename, 'reason': '保存失败：%s' % e})
            continue
        if size > MAX_FILE_BYTES:
            rejected.append({'filename': filename, 'reason': '超过 5MB 上限'})
            _cleanup_files([tmp_path])
            continue
        staged.append({'filename': filename, 'path': tmp_path, 'size': size})

    for f in incoming[MAX_BULK_FILES:]:
        rejected.append({'filename': _safe_filename(f.filename),
                         'reason': '单次最多 %d 个文件' % MAX_BULK_FILES})

    def generate():
        total = len(staged)
        paths = [s['path'] for s in staged]
        ok_cnt = fail_cnt = chunk_total = 0
        try:
            yield _sse({'type': 'start', 'total': total, 'rejected': rejected})

            for i, item in enumerate(staged, 1):
                name = item['filename']

                # ---- 1. 解析 ----
                yield _sse({'type': 'file', 'stage': 'parse', 'index': i,
                            'total': total, 'filename': name,
                            'message': '正在解析「%s」' % name})
                content, parse_err = '', ''
                try:
                    content = _parse_file(item['path'], name)
                except Exception as e:
                    logger.exception('[KB批量] 解析异常: %s', name)
                    parse_err = '解析异常：%s' % e

                if not content or content.startswith('['):
                    fail_cnt += 1
                    reason = parse_err or ('内容为空' if not content
                                           else str(content)[:120])
                    yield _sse({'type': 'file', 'stage': 'error', 'index': i,
                                'total': total, 'filename': name,
                                'message': '解析失败：%s' % reason})
                    continue
                if len(content) > MAX_CONTENT_CHARS:
                    fail_cnt += 1
                    yield _sse({'type': 'file', 'stage': 'error', 'index': i,
                                'total': total, 'filename': name,
                                'message': '内容过长（上限 50 万字）'})
                    continue

                # ---- 2. 切块入库（暂不写向量）----
                yield _sse({'type': 'file', 'stage': 'chunk', 'index': i,
                            'total': total, 'filename': name,
                            'message': '正在切分文本'})
                try:
                    old = KBDocument.query.filter_by(
                        kb_id=kb_id, filename=name).first()
                    if old:
                        old.delete_cascade()
                    doc = KBDocument(kb_id=kb_id, filename=name,
                                     content=content, size=item['size'])
                    db.session.add(doc)
                    db.session.commit()
                    count = kb_service.index_document(doc, with_vectors=False)
                except Exception as e:
                    db.session.rollback()
                    logger.exception('[KB批量] 入库异常: %s', name)
                    fail_cnt += 1
                    yield _sse({'type': 'file', 'stage': 'error', 'index': i,
                                'total': total, 'filename': name,
                                'message': '写入失败：%s' % e})
                    continue

                ok_cnt += 1
                chunk_total += count
                yield _sse({'type': 'file', 'stage': 'done', 'index': i,
                            'total': total, 'filename': name,
                            'chunk_count': count,
                            'message': '已切分 %d 段' % count})

            # ---- 3. 整批统一向量化 ----
            vector_ok, vector_msg = False, ''
            if ok_cnt:
                yield _sse({'type': 'vector', 'stage': 'start', 'done': 0,
                            'total': 0, 'message': '正在向量化文本…'})
                try:
                    from app.services import kb_vector_service as vs
                    for stage, done, tot, msg in vs.iter_rebuild_index(kb_id):
                        if stage == 'progress':
                            yield _sse({'type': 'vector', 'stage': 'progress',
                                        'done': done, 'total': tot,
                                        'message': '正在向量化 %d/%d 段' % (done, tot)})
                        elif stage == 'stored':
                            vector_ok = True
                            yield _sse({'type': 'vector', 'stage': 'done',
                                        'done': tot, 'total': tot,
                                        'message': '向量索引已更新（%d 段）' % tot})
                        elif stage == 'no_chunks':
                            vector_ok = True
                        elif stage == 'no_collection':
                            vector_msg = '向量库不可用，已改用关键词检索'
                            yield _sse({'type': 'vector', 'stage': 'warn',
                                        'done': 0, 'total': tot, 'message': vector_msg})
                        elif stage == 'embed_failed':
                            vector_msg = '向量化服务调用失败，已改用关键词检索'
                            yield _sse({'type': 'vector', 'stage': 'warn',
                                        'done': done, 'total': tot, 'message': vector_msg})
                        else:  # error
                            vector_msg = '向量写入失败：%s' % (msg or '未知错误')
                            yield _sse({'type': 'vector', 'stage': 'warn',
                                        'done': 0, 'total': tot, 'message': vector_msg})
                except Exception as e:
                    logger.exception('[KB批量] 向量化异常')
                    vector_msg = '向量化异常：%s' % e
                    yield _sse({'type': 'vector', 'stage': 'warn',
                                'message': vector_msg})

            yield _sse({'type': 'end', 'success': ok_cnt, 'failed': fail_cnt,
                        'chunks': chunk_total, 'vector_ok': vector_ok,
                        'vector_msg': vector_msg, 'rejected': rejected})
        finally:
            _cleanup_files(paths)

    resp = Response(stream_with_context(generate()),
                    mimetype='text/event-stream')
    # 不要手动设置 Connection: keep-alive —— 会让 werkzeug 不再声明 chunked 结束，
    # 浏览器读不到流结束标记，紧接着的下一个请求会一直挂在同一条连接上。
    resp.headers['Cache-Control'] = 'no-cache, no-transform'
    resp.headers['X-Accel-Buffering'] = 'no'
    return resp


@kb_bp.route('/kb/<kb_id>/documents/<doc_id>', methods=['DELETE'])
def delete_document(kb_id, doc_id):
    uid, err = _require_login()
    if err: return err
    if not KnowledgeBase.is_owner(kb_id, uid):
        return error("只有知识库所有者可以删除文档", 403)
    doc = KBDocument.query.filter_by(id=doc_id, kb_id=kb_id).first()
    if not doc:
        return error("文档不存在", 404)
    doc.delete_cascade()
    return success(None, "文档已删除")


# ---------- 分享管理 ----------

@kb_bp.route('/kb/<kb_id>/shares', methods=['GET'])
def list_shares(kb_id):
    uid, err = _require_login()
    if err: return err
    if not KnowledgeBase.is_owner(kb_id, uid):
        return error("只有知识库所有者可以查看分享列表", 403)
    shares = KBShare.query.filter_by(kb_id=kb_id).all()
    return success([s.to_dict() for s in shares])


@kb_bp.route('/kb/<kb_id>/shares', methods=['POST'])
def add_share(kb_id):
    uid, err = _require_login()
    if err: return err
    kb = KnowledgeBase.query.get(kb_id)
    if not kb:
        return error("知识库不存在", 404)
    if kb.user_id != uid:
        return error("只有知识库所有者可以分享", 403)
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    if not username:
        return error("请输入要分享的用户名", 400)
    target = User.query.filter_by(username=username).first()
    if not target:
        return error("用户不存在", 404)
    if target.id == uid:
        return error("不能分享给自己", 400)
    share, created = KBShare.add(kb_id, uid, target.id)
    if not created:
        return error("已经分享给该用户", 409)
    return success(share.to_dict(), "已分享给 " + username)


@kb_bp.route('/kb/<kb_id>/shares/<share_id>', methods=['DELETE'])
def remove_share(kb_id, share_id):
    uid, err = _require_login()
    if err: return err
    if not KnowledgeBase.is_owner(kb_id, uid):
        return error("只有知识库所有者可以取消分享", 403)
    share = KBShare.query.filter_by(id=share_id, kb_id=kb_id).first()
    if not share:
        return error("分享记录不存在", 404)
    db.session.delete(share)
    db.session.commit()
    return success(None, "已取消分享")


@kb_bp.route('/users/search', methods=['GET'])
def search_users():
    """按用户名搜索用户，供分享时选择"""
    _, err = _require_login()
    if err: return err
    q = (request.args.get('q') or '').strip()
    if not q:
        return success([])
    users = User.query.filter(User.username.like('%' + q + '%')).limit(20).all()
    return success([{'id': u.id, 'username': u.username, 'nickname': u.nickname} for u in users])


# ---------- 检索预览 ----------

@kb_bp.route('/kb/<kb_id>/search', methods=['POST'])
def search_kb(kb_id):
    uid, err = _require_login()
    if err: return err
    if not KnowledgeBase.get_visible(kb_id, uid):
        return error("知识库不存在或无访问权限", 404)
    data = request.get_json() or {}
    query = (data.get('query') or '').strip()
    if not query:
        return error("查询内容不能为空", 400)
    results = kb_service.retrieve(kb_id, query, top_k=5)
    return success([{'doc_name': c.doc_name, 'position': c.position,
                     'content': c.content, 'score': round(s, 2)} for c, s in results])
