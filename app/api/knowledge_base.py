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
import re
import shutil
import uuid
from flask import Blueprint, Response, request, session, stream_with_context, send_file
from app.models.user import User
from app.models.knowledge_base import (KnowledgeBase, KBDocument, KBChunk, KBTable,
                                       KBShare, KBStaging, KBStagingChunk)
from app.services import kb_service
from app.utils.response import success, error
from app.extensions import db

kb_bp = Blueprint('knowledge_base', __name__)
logger = logging.getLogger(__name__)

ALLOWED = {'txt', 'md', 'pdf', 'docx', 'doc', 'xlsx', 'xlsm', 'py', 'js', 'html', 'css',
           'json', 'xml', 'csv', 'log', 'java', 'c', 'cpp', 'h'}
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_BULK_FILES = 20              # 单次批量上传最多文件数
MAX_FILE_BYTES = 5 * 1024 * 1024  # 单文件上限 5MB
MAX_CONTENT_CHARS = 500000        # 单文档正文上限 50 万字

# 原文件留存目录：下载表格时返回上传的原件本身，绝不重新生成
ORIGINAL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'kb_originals')
os.makedirs(ORIGINAL_DIR, exist_ok=True)


def _retain_original(tmp_path, kb_id, filename):
    """把上传的原文件复制到留存目录，返回可访问的绝对路径。"""
    rel_dir = os.path.join(ORIGINAL_DIR, kb_id)
    os.makedirs(rel_dir, exist_ok=True)
    dest = os.path.join(rel_dir, '%s_%s' % (uuid.uuid4().hex[:12], filename))
    shutil.copy2(tmp_path, dest)
    return dest


def _save_tables(kb_id, doc, parsed_tables, original_path):
    """把抽取出的真实表格写入 kb_tables；返回表格数。"""
    count = 0
    for t in parsed_tables:
        try:
            row = KBTable(
                kb_id=kb_id, doc_id=doc.id, doc_name=doc.filename,
                table_name=t['table_name'], source=t['source'],
                rows_json=json.dumps(t['rows'], ensure_ascii=False),
                merges_json=json.dumps(t.get('merges', []), ensure_ascii=False),
                row_count=t['row_count'], col_count=t['col_count'],
                fill_rate=t['fill_rate'],
                original_path=original_path, original_name=doc.filename,
            )
            db.session.add(row)
            count += 1
        except Exception as e:
            logger.warning('[KB表格] 保存表格失败 %s: %s', t.get('table_name'), e)
    if count:
        db.session.commit()
    return count


def _stage_document(kb_id, filename, content, file_size, original_path,
                    parsed_tables, uploaded_by):
    """把解析结果写入待审核区（不进正式表、不建向量索引）。

    正文按语义切块，表格作为独立块，两者交错按原顺序存 position。
    返回 (staging, 文本块数, 表格块数)。
    """
    stage = KBStaging(
        kb_id=kb_id, filename=filename, size=file_size,
        original_path=original_path, uploaded_by=uploaded_by or '',
    )
    db.session.add(stage)
    db.session.flush()  # 拿到 stage.id

    # 文本块：结构化切分（制度类识别标题层级，块带章节路径和页码）
    structured = kb_service.split_structured(content, with_page=True)
    text_units = [('text', c, path, page) for path, c, page in structured]

    # 表格块：content 用文本化描述（供审核时读懂），结构化数据单独存。
    # 从 source（如「PDF 第3页 第1个表格」）解析页码，用于按文档顺序归位。
    table_pages = re.compile(r'第\s*(\d+)\s*页')
    tables_by_page = {}   # page -> [table dict]，保持原顺序
    no_page_tables = []
    for t in parsed_tables:
        m = table_pages.search(t.get('source', '') or '')
        if m:
            tables_by_page.setdefault(int(m.group(1)), []).append(t)
        else:
            no_page_tables.append(t)

    def table_unit(t):
        desc = '%s（%d行×%d列）' % (t.get('table_name', '表格'),
                                   t.get('row_count', 0), t.get('col_count', 0))
        return ('table', desc, t)

    # 按文档顺序交错：遍历文本块，把表格插到「该页最后一个文本块」之后。
    # 表格不拆散，同页多表按抽取顺序排列。
    units = []
    flushed_pages = set()
    total = len(text_units)
    for idx, item in enumerate(text_units):
        units.append(item[:3])   # (kind, content, meta)
        page = item[3]
        if not page or page not in tables_by_page or page in flushed_pages:
            continue
        # 该页后续还有文本块 → 等最后一个再插
        if any(text_units[j][3] == page for j in range(idx + 1, total)):
            continue
        for t in tables_by_page[page]:
            units.append(table_unit(t))
        flushed_pages.add(page)
    # 未能归位的表格（无页码或页码不在文本块范围内）追加到末尾，保证不丢失
    for page in sorted(tables_by_page):
        if page not in flushed_pages:
            for t in tables_by_page[page]:
                units.append(table_unit(t))
    for t in no_page_tables:
        units.append(table_unit(t))
    text_cnt = table_cnt = 0
    for pos, item in enumerate(units):
        kind, text, meta = item
        section_path = meta if kind == 'text' else ''
        tbl = meta if kind == 'table' else None
        chunk = KBStagingChunk(
            staging_id=stage.id, kb_id=kb_id, kind=kind, position=pos,
            content=text, section_path=section_path,
        )
        if kind == 'table' and tbl:
            chunk.rows_json = json.dumps(tbl.get('rows', []), ensure_ascii=False)
            chunk.merges_json = json.dumps(tbl.get('merges', []), ensure_ascii=False)
            chunk.table_name = tbl.get('table_name', '')
            chunk.source = tbl.get('source', '')
            chunk.original_name = filename
            chunk.row_count = tbl.get('row_count', 0)
            chunk.col_count = tbl.get('col_count', 0)
            chunk.fill_rate = tbl.get('fill_rate', 0.0)
            table_cnt += 1
        else:
            text_cnt += 1
        db.session.add(chunk)

    stage.chunk_count = text_cnt
    stage.table_count = table_cnt
    db.session.commit()
    return stage, text_cnt, table_cnt


def _parse_tables_safe(tmp_path, filename):
    """抽取表格；失败不影响正文入库，返回空列表。"""
    try:
        from app.services import kb_table_service as ts
        return ts.extract_tables(tmp_path, filename)
    except Exception as e:
        logger.warning('[KB表格] 解析失败（不影响正文）%s: %s', filename, e)
        return []


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

    tmp_path = os.path.join(UPLOAD_DIR, ('kb_' + uuid.uuid4().hex[:8] + '_' + filename))
    original_path = None
    parsed_tables = []
    try:
        file.save(tmp_path)
        file_size = os.path.getsize(tmp_path)
        content = _parse_file(tmp_path, filename)
        # 在临时文件删除前：留存原件 + 抽取结构化表格
        original_path = _retain_original(tmp_path, kb_id, filename)
        parsed_tables = _parse_tables_safe(tmp_path, filename)
    finally:
        # 临时文件清理失败不能影响已经成功的解析结果
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception as e:
            logger.warning('[KB上传] 临时文件清理失败（不影响入库）：%s', e)

    if not content or content.startswith('[错误]'):
        if original_path and os.path.exists(original_path):
            try: os.remove(original_path)
            except Exception: pass
        return error("文档解析失败或内容为空：" + str(content)[:100], 400)

    stage, text_cnt, table_cnt = _stage_document(
        kb_id, filename, content, file_size, original_path, parsed_tables, uid)
    return success({'id': stage.id, 'filename': filename, 'staging': True,
                    'chunk_count': text_cnt, 'table_count': table_cnt},
                   "文档已解析完成，等待审核；审核通过后才会进入知识库")


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
                table_data = []       # 本文件的结构化表格
                original_path = None  # 本文件的留存原件路径
                try:
                    content = _parse_file(item['path'], name)
                    # 在临时文件清理前：留存原件 + 抽取表格
                    original_path = _retain_original(item['path'], kb_id, name)
                    table_data = _parse_tables_safe(item['path'], name)
                except Exception as e:
                    logger.exception('[KB批量] 解析异常: %s', name)
                    parse_err = '解析异常：%s' % e

                if not content or content.startswith('[错误]'):
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

                # 表格文本并入正文，供向量检索命中
                if table_data:
                    from app.services import kb_table_service as ts
                    content = (content + '\n\n' + ts.tables_to_text(table_data))[:MAX_CONTENT_CHARS]

                # ---- 2. 切块 → 落入待审核区（不进正式表、不向量化）----
                yield _sse({'type': 'file', 'stage': 'chunk', 'index': i,
                            'total': total, 'filename': name,
                            'message': '正在切分文本'})
                try:
                    stage, text_cnt, table_cnt = _stage_document(
                        kb_id, name, content, item['size'], original_path,
                        table_data, uid)
                    count = text_cnt + table_cnt
                except Exception as e:
                    db.session.rollback()
                    logger.exception('[KB批量] 待审核区写入异常: %s', name)
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
                            'message': '已切分 %d 段，等待审核' % count})

            # 审核前不做向量化；向量化在用户点击"通过审核"时触发
            yield _sse({'type': 'end', 'success': ok_cnt, 'failed': fail_cnt,
                        'chunks': chunk_total, 'vector_ok': False,
                        'vector_msg': '文档已解析，请在待审核区确认后再入库',
                        'need_review': True, 'rejected': rejected})
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


# ---------- 待审核区（人工把关后才入库） ----------

@kb_bp.route('/kb/<kb_id>/staging', methods=['GET'])
def list_staging(kb_id):
    """待审核文档列表（仅 owner 可见）。"""
    uid, err = _require_login()
    if err: return err
    if not KnowledgeBase.is_owner(kb_id, uid):
        return error("只有知识库所有者可以查看待审核区", 403)
    rows = KBStaging.query.filter_by(kb_id=kb_id).order_by(
        KBStaging.created_at.desc()).all()
    return success([r.to_dict() for r in rows])


@kb_bp.route('/kb/<kb_id>/staging/<stage_id>', methods=['GET'])
def get_staging(kb_id, stage_id):
    """待审核文档详情：含全部切片（文本块 + 独立表格块）。"""
    uid, err = _require_login()
    if err: return err
    if not KnowledgeBase.is_owner(kb_id, uid):
        return error("只有知识库所有者可以查看待审核区", 403)
    stage = KBStaging.query.filter_by(id=stage_id, kb_id=kb_id).first()
    if not stage:
        return error("待审核文档不存在", 404)
    d = stage.to_dict()
    d['chunks'] = [c.to_dict() for c in stage.chunks()]
    return success(d)


@kb_bp.route('/kb/<kb_id>/staging/<stage_id>/chunks/<chunk_id>', methods=['PUT'])
def edit_staging_chunk(kb_id, stage_id, chunk_id):
    """编辑切片：支持改正文、改章节标题（section_path）、改表格名。

    section_path 是检索时聚合父块的依据，也是审核列表里显示的绿色标题；
    自动识别可能出错，审核时允许人工修正。
    """
    uid, err = _require_login()
    if err: return err
    if not KnowledgeBase.is_owner(kb_id, uid):
        return error("只有知识库所有者可以审核", 403)
    chunk = KBStagingChunk.query.filter_by(
        id=chunk_id, staging_id=stage_id, kb_id=kb_id).first()
    if not chunk:
        return error("切片不存在", 404)
    data = request.get_json(silent=True) or {}

    content = data.get('content')
    if content is not None:
        if not str(content).strip():
            return error("切片内容不能为空", 400)
        chunk.content = str(content).strip()

    if 'section_path' in data:
        path = str(data.get('section_path') or '').strip()
        if len(path) > 500:
            return error("章节标题不能超过 500 字", 400)
        chunk.section_path = path

    if 'table_name' in data and chunk.kind == 'table':
        name = str(data.get('table_name') or '').strip()
        if name:
            chunk.table_name = name[:255]

    db.session.commit()
    return success(chunk.to_dict(), "切片已更新")


@kb_bp.route('/kb/<kb_id>/staging/<stage_id>/chunks/<chunk_id>', methods=['DELETE'])
def delete_staging_chunk(kb_id, stage_id, chunk_id):
    """删除错误切片（审核时剔除解析错误的内容）。"""
    uid, err = _require_login()
    if err: return err
    if not KnowledgeBase.is_owner(kb_id, uid):
        return error("只有知识库所有者可以审核", 403)
    chunk = KBStagingChunk.query.filter_by(
        id=chunk_id, staging_id=stage_id, kb_id=kb_id).first()
    if not chunk:
        return error("切片不存在", 404)
    stage = KBStaging.query.get(stage_id)
    db.session.delete(chunk)
    if stage:
        if chunk.kind == 'table':
            stage.table_count = max(0, (stage.table_count or 0) - 1)
        else:
            stage.chunk_count = max(0, (stage.chunk_count or 0) - 1)
    db.session.commit()
    return success(None, "切片已删除")


@kb_bp.route('/kb/<kb_id>/staging/<stage_id>/chunks/merge', methods=['POST'])
def merge_staging_chunks(kb_id, stage_id):
    """合并相邻文本切片（修复被切散的段落）。仅支持纯文本块。"""
    uid, err = _require_login()
    if err: return err
    if not KnowledgeBase.is_owner(kb_id, uid):
        return error("只有知识库所有者可以审核", 403)
    data = request.get_json(silent=True) or {}
    ids = data.get('ids') or []
    if not isinstance(ids, list) or len(ids) < 2:
        return error("请至少选择两个切片合并", 400)
    chunks = KBStagingChunk.query.filter(
        KBStagingChunk.staging_id == stage_id,
        KBStagingChunk.kb_id == kb_id,
        KBStagingChunk.id.in_(ids),
    ).order_by(KBStagingChunk.position).all()
    if len(chunks) != len(ids):
        return error("部分切片不存在", 404)
    if any(c.kind != 'text' for c in chunks):
        return error("表格块不能与文本块合并", 400)
    merged_text = '\n'.join(c.content for c in chunks if c.content)
    first = chunks[0]
    first.content = merged_text
    stage = KBStaging.query.get(stage_id)
    for c in chunks[1:]:
        db.session.delete(c)
    if stage:
        stage.chunk_count = max(1, (stage.chunk_count or 0) - (len(chunks) - 1))
    db.session.commit()
    return success(first.to_dict(), "已合并 %d 个切片" % len(chunks))


@kb_bp.route('/kb/<kb_id>/staging/<stage_id>/approve', methods=['POST'])
def approve_staging(kb_id, stage_id):
    """审核通过：把切片写入正式表、抽取表格入库、触发向量化。

    这是数据进入知识库的唯一入口——审核前的解析结果对检索完全不可见。
    """
    uid, err = _require_login()
    if err: return err
    if not KnowledgeBase.is_owner(kb_id, uid):
        return error("只有知识库所有者可以通过审核", 403)
    stage = KBStaging.query.filter_by(id=stage_id, kb_id=kb_id).first()
    if not stage:
        return error("待审核文档不存在", 404)
    chunks = stage.chunks()
    if not chunks:
        return error("没有可入库的切片，请先驳回", 400)

    # 同名正式文档先删除（避免重复入库）
    old = KBDocument.query.filter_by(kb_id=kb_id, filename=stage.filename).first()
    if old:
        old.delete_cascade()

    try:
        # 正式文档正文 = 审核后的文本块重新拼回
        text_contents = [c.content for c in chunks
                         if c.kind == 'text' and c.content]
        body = '\n\n'.join(text_contents)
        doc = KBDocument(
            kb_id=kb_id, filename=stage.filename, content=body,
            size=stage.size or 0, original_path=stage.original_path,
            table_count=stage.table_count or 0,
        )
        db.session.add(doc)
        db.session.flush()

        text_cnt = table_cnt = 0
        for c in chunks:
            if c.kind == 'table':
                row = KBTable(
                    kb_id=kb_id, doc_id=doc.id, doc_name=stage.filename,
                    table_name=c.table_name or '表格', source=c.source or '',
                    rows_json=c.rows_json or '[]', merges_json=c.merges_json or '[]',
                    row_count=c.row_count or 0, col_count=c.col_count or 0,
                    fill_rate=c.fill_rate or 0.0,
                    original_path=stage.original_path,
                    original_name=c.original_name or stage.filename,
                )
                db.session.add(row)
                table_cnt += 1
            else:
                chunk = KBChunk(
                    kb_id=kb_id, doc_id=doc.id, doc_name=stage.filename,
                    content=c.content, position=text_cnt,
                    section_path=getattr(c, 'section_path', '') or '',
                )
                db.session.add(chunk)
                text_cnt += 1
        doc.chunk_count = text_cnt
        doc.table_count = table_cnt

        # 表格文本化后也作为检索块写入，保证表格数据能被问答命中
        from app.services import kb_table_service as ts
        table_rows = [c for c in chunks if c.kind == 'table']
        table_texts = ts.tables_to_text([
            {'table_name': c.table_name, 'rows': c._loads(c.rows_json),
             'row_count': c.row_count, 'col_count': c.col_count,
             'source': c.source}
            for c in table_rows
        ]) if table_rows else ''
        if table_texts:
            db.session.add(KBChunk(
                kb_id=kb_id, doc_id=doc.id, doc_name=stage.filename,
                content=table_texts, position=text_cnt,
            ))
            doc.chunk_count = text_cnt + 1

        # 删除待审核记录（保留原件，正式表已引用同一路径）
        KBStagingChunk.query.filter_by(staging_id=stage.id).delete()
        db.session.delete(stage)
        db.session.commit()

        # 整库重建向量索引
        vector_msg = ''
        try:
            from app.services import kb_vector_service as vs
            ok = vs.rebuild_index(kb_id)
            vector_msg = '向量索引已更新' if ok else '向量库不可用，已保留关键词检索'
        except Exception as e:
            logger.warning('[审核] 向量化失败: %s', e)
            vector_msg = '向量化失败：%s' % e

        return success({'doc_id': doc.id, 'chunk_count': doc.chunk_count,
                        'table_count': table_cnt, 'vector_msg': vector_msg},
                       "审核通过，文档已正式入库")
    except Exception as e:
        db.session.rollback()
        logger.exception('[审核] 入库失败')
        return error("入库失败：%s" % e, 500)


@kb_bp.route('/kb/<kb_id>/staging/<stage_id>', methods=['DELETE'])
def reject_staging(kb_id, stage_id):
    """驳回待审核文档：丢弃解析结果和留存原件，不进知识库。"""
    uid, err = _require_login()
    if err: return err
    if not KnowledgeBase.is_owner(kb_id, uid):
        return error("只有知识库所有者可以驳回", 403)
    stage = KBStaging.query.filter_by(id=stage_id, kb_id=kb_id).first()
    if not stage:
        return error("待审核文档不存在", 404)
    stage.delete_cascade(remove_original=True)
    return success(None, "已驳回并丢弃该文档")


# ---------- 表格清单与原件下载 ----------

def legacy_download_response(legacy_id=None):
    """兼容早期版本遗留的旧下载链接 /api/kb/download/<id>?file=<uuid>。

    这些链接指向的文档在UI中已被删除/重建，file UUID 在当前库里不存在，
    无法映射到任何真实原件。按"只返回真实存在文件"的铁律，绝不随便挑一个
    文件顶替；返回一个带说明的页面，引导用户回知识库重新提问获取新链接。
    """
    file_uuid = (request.args.get('file') or '').strip()
    # 尽力而为：若旧 UUID 恰好命中当前某张表的原件名/路径，才放行真实原件
    row = None
    if file_uuid:
        row = KBTable.query.filter(
            KBTable.original_path.like('%' + file_uuid + '%')
        ).first()
    if row and row.original_path and os.path.exists(row.original_path):
        return send_file(row.original_path, as_attachment=True,
                         download_name=row.original_name or os.path.basename(row.original_path))
    # 找不到对应原件：返回可读页面，而非 JSON 404（IDM 会显示"无法下载-没有文件"）
    html = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>下载链接已过期</title>
<style>body{font-family:system-ui,"Microsoft YaHei",sans-serif;background:#f5f6f8;color:#1f2937;
display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
.box{background:#fff;padding:32px 36px;border-radius:12px;max-width:460px;box-shadow:0 4px 20px rgba(0,0,0,.08)}
h1{font-size:20px;margin:0 0 12px}p{line-height:1.7;color:#4b5563;font-size:14px}
a{display:inline-block;margin-top:16px;padding:10px 18px;background:#2563eb;color:#fff;
border-radius:8px;text-decoration:none;font-size:14px}</style></head><body><div class="box">
<h1>这个下载链接已经过期</h1>
<p>它来自旧版本的知识库问答，指向的文件已被删除或重新上传，系统中已没有对应的原件，因此无法下载。</p>
<p>请回到知识库，重新提问需要的文件或表格，助手会给你一条新的下载链接。</p>
<a href="/">返回知识库助手</a></div></body></html>'''
    return Response(html, status=200, content_type='text/html; charset=utf-8')


@kb_bp.route('/kb/download/<legacy_id>', methods=['GET'])
def legacy_download_v1(legacy_id):
    return legacy_download_response(legacy_id)


@kb_bp.route('/kb/<kb_id>/tables', methods=['GET'])
def list_kb_tables(kb_id):
    """列出知识库里真实抽取到的表格（不含生成内容）。"""
    _, err = _require_login()
    if err: return err
    if not KnowledgeBase.get_visible(kb_id, _uid()):
        return error("知识库不存在或无访问权限", 404)
    rows = KBTable.query.filter_by(kb_id=kb_id) \
        .order_by(KBTable.doc_name, KBTable.created_at).all()
    return success([r.to_dict() for r in rows])


@kb_bp.route('/kb/<kb_id>/tables/<table_id>', methods=['GET'])
def get_kb_table(kb_id, table_id):
    """获取单张表格的行列内容（供核对预览）。"""
    _, err = _require_login()
    if err: return err
    if not KnowledgeBase.get_visible(kb_id, _uid()):
        return error("知识库不存在或无访问权限", 404)
    row = KBTable.query.filter_by(id=table_id, kb_id=kb_id).first()
    if not row:
        return error("表格不存在", 404)
    return success(row.to_dict(include_rows=True))


@kb_bp.route('/kb/<kb_id>/tables/<table_id>/download', methods=['GET'])
def download_kb_table(kb_id, table_id):
    """下载表格所在的原始文件。

    铁律：只从留存目录取上传时的原件返回；原件不存在则 404。
    绝不根据表格数据重新生成文件，避免产出知识库里不存在的表格。
    """
    # 有登录态时做常规权限校验；无登录态时（IDM / 迅雷等下载器接管请求不带 Cookie）
    # 依赖 URL 里的 kb_id + table_id（UUID，不可枚举）作为 capability URL 放行，
    # 否则这些下载器会收到 401 并报"无法下载 - 没有文件"。
    uid = session.get('user_id')
    if uid and not KnowledgeBase.get_visible(kb_id, uid):
        return error("知识库不存在或无访问权限", 404)
    row = KBTable.query.filter_by(id=table_id, kb_id=kb_id).first()
    # 旧卡片/旧页面可能存着已删除的表格 id（文档重新上传后旧记录被清理）。
    # 用卡片携带的文档名回退到当前同名文档的最新表格，让下载不再失效。
    # 铁律不变：只返回真实存在的原件，绝不生成文件。
    if not row:
        doc_hint = (request.args.get('doc') or '').strip()
        if doc_hint:
            row = KBTable.query.filter(
                KBTable.kb_id == kb_id,
                KBTable.doc_name == doc_hint,
            ).order_by(KBTable.created_at.desc()).first()
    if not row:
        return error("表格不存在或已被更新，请重新上传文档后再下载", 404)
    path = row.original_path
    if not path or not os.path.exists(path):
        # 没有留存原件时明确告知，绝不生成替代文件
        return error("该表格的原文件不存在（旧版本上传的文档未留存原件），无法下载", 404)
    download_name = row.original_name or os.path.basename(path)
    return send_file(path, as_attachment=True, download_name=download_name)


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
