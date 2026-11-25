"""
聊天模块 API 路由
====================
提供对话相关的 RESTful 接口，包括：
- 普通同步对话接口
- 流式（SSE）对话接口
- 文件附件处理与上下文拼接
"""
from flask import Blueprint, request, Response, stream_with_context, session
from app.services.chat_service import ChatService
from app.services.model_service import ModelService
from app.models.conversation import Conversation
from app.models.message import Message
from app.llm.memory import ConversationMemory
from app.config.settings import settings
from app.utils.response import success, error

# 创建名为 'chat' 的蓝图，用于组织聊天相关的路由
chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chat', methods=['POST'])
def chat():
    """
    普通对话接口（同步）
    --------------------------
    接收用户消息并返回 AI 的完整回复（非流式）。
    适用于无需实时显示生成过程的场景。

    请求体 JSON 字段:
        - message (必填): 用户输入的文本
        - conversation_id (可选): 会话 ID，默认 "default"
        - model (可选): 模型类型
        - system_prompt (可选): 系统提示词
        - role_id (可选): 角色 ID

    返回:
        JSON 格式的成功响应，包含 AI 回复内容
    """
    data = request.get_json()
    if not data or 'message' not in data:
        return error("message 参数不能为空", 400)

    # VIP限流
    uid = session.get('user_id','')
    if uid:
        from app.models.user import User as _U
        u = _U.find_by_id(uid)
        if u and not u.can_chat_today()[0]: return error(f'今日免费额度已用完', 429)
        if u: u.record_chat()
    try:
        # 会话模式：normal=普通问答，kb=知识库问答
        mode = data.get('mode', 'normal')
        mode = mode if mode in ('normal', 'kb') else 'normal'
        kb_id = (data.get('kb_id', '') or '') if mode == 'kb' else ''
        role_id = data.get('role_id') if mode == 'normal' else None
        sys_prompt = data.get('system_prompt') if mode == 'normal' else None
        if mode == 'kb' and not kb_id:
            return error("请选择知识库", 400)

        # 知识库问答：检索相关片段并注入 system prompt
        if mode == 'kb':
            from app.models.knowledge_base import KnowledgeBase
            from app.services import kb_service
            kb = KnowledgeBase.get_visible(kb_id, session.get('user_id', ''))
            if not kb:
                return error("知识库不存在或无访问权限", 404)
            context = kb_service.build_context(kb_id, data['message'])
            if not context:
                return error("知识库中暂无可检索的内容，请先上传文档", 400)
            sys_prompt = kb_service.kb_system_prompt(kb.name, context, None)

        # 调用聊天服务层处理对话逻辑
        result = ChatService.chat(
            conversation_id=data.get('conversation_id', 'default'),
            user_input=data['message'],
            model_type=data.get('model'),
            system_prompt=sys_prompt,
            role_id=role_id,
            mode=mode,
            kb_id=kb_id,
        )
        # 将新会话绑定当前用户
        uid = session.get('user_id','')
        if uid and result:
            conv = Conversation.query.get(result['conversation_id'])
            if conv and (not conv.user_id or conv.user_id == 'anonymous'):
                conv.user_id = uid
                from app.extensions import db as _db3
                _db3.session.commit()
        return success(result)
    except ValueError as e:
        # 参数校验错误，返回 400
        return error(str(e), 400)
    except Exception as e:
        # 其他服务器内部错误，返回 500
        return error(f"对话失败: {str(e)}", 500)


@chat_bp.route('/chat/stream', methods=['POST'])
def chat_stream():
    """
    流式对话接口（SSE - Server-Sent Events）
    ------------------------------------------
    使用 Server-Sent Events 协议将 AI 回复逐字推送给前端。
    支持文件附件内容自动拼接到 LLM 上下文中，
    但附件内容仅用于推理，不会被持久化到消息记录中。

    请求体 JSON 字段:
        - message (必填): 用户输入的文本
        - conversation_id (可选): 会话 ID，默认 "default"
        - model (可选): 模型类型
        - system_prompt (可选): 系统提示词
        - role_id (可选): 角色 ID
        - params (可选): 模型参数（如 temperature、top_p 等）
        - attachment (可选): 附件信息，包含 filename 和 content

    返回:
        text/event-stream 格式的 SSE 流
    """
    data = request.get_json()
    if not data or 'message' not in data:
        return error("message 参数不能为空", 400)

    conversation_id = data.get('conversation_id', 'default')
    original_message = data['message']  # 用户原始输入（存数据库时使用）
    user_input = original_message
    model_type = data.get('model')
    mode = data.get('mode', 'normal')
    mode = mode if mode in ('normal', 'kb') else 'normal'
    system_prompt = data.get('system_prompt') if mode == 'normal' else None
    role_id = data.get('role_id') if mode == 'normal' else None
    model_params = data.get('params', {})
    attachment = data.get('attachment', {})
    attach_filename = ''
    kb_id = (data.get('kb_id', '') or '') if mode == 'kb' else ''

    # 知识库问答：检索相关片段并注入 system prompt
    kb_context_error = None
    if mode == 'kb' and not kb_id:
        kb_context_error = "请选择知识库"
    elif mode == 'kb':
        from app.models.knowledge_base import KnowledgeBase
        from app.services import kb_service
        uid_kb = session.get('user_id', '')
        kb = KnowledgeBase.get_visible(kb_id, uid_kb)
        if not kb:
            kb_context_error = "知识库不存在或无访问权限"
        else:
            context = kb_service.build_context(kb_id, original_message)
            if not context:
                kb_context_error = "知识库中暂无可检索的内容，请先上传文档"
            else:
                system_prompt = kb_service.kb_system_prompt(kb.name, context, None)

    # 有附件时，将文件内容拼接到 LLM 上下文中（但不存入数据库）
    if attachment and attachment.get('content'):
        attach_filename = attachment.get('filename', '文件')
        # 构造包含文件内容的提示文本，作为 LLM 的上下文输入
        file_ctx = f"[用户上传了文件: {attach_filename}]\n\n文件内容:\n```\n{attachment['content']}\n```\n\n基于以上文件内容，回答用户问题:\n"
        user_input = file_ctx + original_message

    # VIP限流
    uid2 = session.get('user_id','')
    if uid2:
        from app.models.user import User as _U2
        u2 = _U2.find_by_id(uid2)
        if u2 and not u2.can_chat_today()[0]:
            def gen_err(): yield 'data: [ERROR] 今日免费额度已用完，请升级VIP\n\n'
            return Response(gen_err(), mimetype='text/event-stream')
        if u2: u2.record_chat()
    def generate():
        """
        生成器函数 —— 负责逐步产生 SSE 事件数据。
        内部流程包括:
            1. 准备会话上下文（会话对象、记忆、消息列表）
            2. 获取模型客户端，逐块流式生成回复
            3. 将完整的用户消息和 AI 回复持久化到数据库
            4. 若为新会话则自动更新标题
        """
        import json as _json
        try:
            # 知识库模式：智能推荐表格。
            # 对用户的任何提问，都在真实表格库里按"问题语义"匹配；
            # 命中则给下载卡片，未命中则不给链接。两种情况都不让模型生成表格。
            table_hit = None
            explicit_want = False
            if mode == 'kb' and kb_id:
                from app.services import kb_table_service as ts
                from app.models.knowledge_base import KBTable
                explicit_want = ts.wants_table(original_message)
                # 权限类错误仍需拦截，仅对"暂无可检索内容"放行（表格可独立命中）
                if kb_context_error and '暂无可检索' not in kb_context_error \
                        and not explicit_want:
                    yield 'data: [ERROR] ' + kb_context_error + '\n\n'
                    return
                tables = KBTable.query.filter_by(kb_id=kb_id).all()
                hit, score = ts.match_table(original_message, tables)
                # 明确索要时门槛低一些，智能推荐时门槛高一些，避免误推
                threshold = 0.40 if explicit_want else 0.55
                if hit and score >= threshold:
                    table_hit = hit

                # 表格名是"表格 1"这类默认值时，用文档名作为展示名
                def _display_name(tb):
                    import re as _re
                    n = tb.table_name or ''
                    if _re.match(r'^表格\s*\d+$', n) and tb.doc_name:
                        return _re.sub(r'\.[^.]+$', '', tb.doc_name)
                    return n

                # 明确索要表格：直接给结果，不走大模型（杜绝生成不存在的表格）
                if explicit_want:
                    if table_hit:
                        hint = '在知识库中找到表格「%s」，这是上传的原始文件，可直接下载：\n\n' \
                               % _display_name(table_hit)
                        for ch in hint:
                            yield 'data: ' + _json.dumps(ch) + '\n\n'
                        yield 'data: ' + _json.dumps(ts.table_hit_payload(table_hit)) + '\n\n'
                        answer = '已返回表格「%s」的下载链接' % _display_name(table_hit)
                    else:
                        answer = '知识库中没有找到你需要的表格。我只提供库中已上传的真实文件，不会生成新表格。'
                        for ch in answer:
                            yield 'data: ' + _json.dumps(ch) + '\n\n'
                    conv_tbl, _, _ = ChatService.prepare_chat_context(
                        conversation_id, original_message, model_type, None, None,
                        mode=mode, kb_id=kb_id,
                    )
                    Message.create(conv_tbl.id, 'user', original_message)
                    # 把下载卡片标记写进消息，刷新后可还原
                    stored_answer = answer
                    if table_hit:
                        stored_answer = ts.embed_card_marker(
                            hint + answer, ts.table_hit_payload(table_hit)['__table_card__'])
                    Message.create(conv_tbl.id, 'assistant', stored_answer)
                    yield "data: [DONE]\n\n"
                    return

            # 知识库错误按原逻辑拦截
            if kb_context_error:
                yield 'data: [ERROR] ' + kb_context_error + '\n\n'
                return

            # 步骤1: 准备对话上下文（包含历史消息加载和记忆注入）
            uid = session.get('user_id',''); conversation, memory, messages = ChatService.prepare_chat_context(
                conversation_id, user_input, model_type, system_prompt, role_id,
                mode=mode, kb_id=kb_id,
            )
            # 将新创建的会话绑定到当前登录用户
            if uid and (not conversation.user_id or conversation.user_id == 'anonymous'):
                conversation.user_id = uid
                from app.extensions import db as _db2
                _db2.session.commit()

            # 步骤2: 获取模型客户端并开始流式生成
            model_client = ModelService.get_model_client(model_type, model_params)
            full_response = ""

            for chunk in model_client.stream(messages):
                full_response += chunk
                # 以 SSE 格式推送每个数据块: "data: <json>\n\n"
                yield f"data: {_json.dumps(chunk)}\n\n"

            # 步骤3: 组装要持久化的回答。
            # 高置信度命中真实表格时，把推荐文字 + 下载卡片标记一起存进消息，
            # 这样刷新页面回放历史时也能还原卡片（标记不生成表格，只存真实文件链接）。
            stored_answer = full_response
            table_tip = ''
            table_card = None
            if table_hit is not None:
                from app.services import kb_table_service as ts
                _name = table_hit.table_name or ''
                import re as _re
                if _re.match(r'^表格\s*\d+$', _name) and table_hit.doc_name:
                    _name = _re.sub(r'\.[^.]+$', '', table_hit.doc_name)
                table_tip = '\n\n另外，知识库里有你可能需要的表格「%s」，可直接下载原文件：' % _name
                table_card = ts.table_hit_payload(table_hit)['__table_card__']
                stored_answer = ts.embed_card_marker(full_response + table_tip, table_card)

            # 将原始消息（不包含文件内容）保存到数据库
            display_msg = original_message
            if attach_filename:
                display_msg = '📎 '+attach_filename+'\n'+original_message
            Message.create(conversation.id, "user", display_msg)
            Message.create(conversation.id, "assistant", stored_answer)

            # 步骤4: 若是新建会话（标题为"新对话"），
            # 自动根据用户的第一条输入生成会话标题
            if conversation.title == "新对话":
                conversation.title = user_input[:30] + ("..." if len(user_input) > 30 else "")
                from app.extensions import db
                db.session.commit()

            # 步骤5: 实时推送推荐文字与卡片事件（存库已在上面完成）
            if table_tip:
                for ch in table_tip:
                    yield 'data: ' + _json.dumps(ch) + '\n\n'
                yield 'data: ' + _json.dumps({'__table_card__': table_card}) + '\n\n'

            # 发送流结束标记
            yield "data: [DONE]\n\n"

        except Exception as e:
            # 流式过程中发生异常时，向客户端推送错误信息
            yield f"data: [ERROR] {str(e)}\n\n"

    # 返回 SSE 流式响应，设置必要的响应头以支持流式传输
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',      # 禁用缓存，确保实时推送
            'X-Accel-Buffering': 'no',        # 禁用 Nginx 缓冲（若使用 Nginx 代理）
        }
    )
