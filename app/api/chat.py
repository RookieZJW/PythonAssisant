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

    try:
        # 调用聊天服务层处理对话逻辑
        result = ChatService.chat(
            conversation_id=data.get('conversation_id', 'default'),
            user_input=data['message'],
            model_type=data.get('model'),
            system_prompt=data.get('system_prompt'),
            role_id=data.get('role_id'),
        )
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
    system_prompt = data.get('system_prompt')
    role_id = data.get('role_id')
    model_params = data.get('params', {})
    attachment = data.get('attachment', {})
    attach_filename = ''

    # 有附件时，将文件内容拼接到 LLM 上下文中（但不存入数据库）
    if attachment and attachment.get('content'):
        attach_filename = attachment.get('filename', '文件')
        # 构造包含文件内容的提示文本，作为 LLM 的上下文输入
        file_ctx = f"[用户上传了文件: {attach_filename}]\n\n文件内容:\n```\n{attachment['content']}\n```\n\n基于以上文件内容，回答用户问题:\n"
        user_input = file_ctx + original_message

    def generate():
        """
        生成器函数 —— 负责逐步产生 SSE 事件数据。
        内部流程包括:
            1. 准备会话上下文（会话对象、记忆、消息列表）
            2. 获取模型客户端，逐块流式生成回复
            3. 将完整的用户消息和 AI 回复持久化到数据库
            4. 若为新会话则自动更新标题
        """
        try:
            # 步骤1: 准备对话上下文（包含历史消息加载和记忆注入）
            uid = session.get('user_id',''); conversation, memory, messages = ChatService.prepare_chat_context(
                conversation_id, user_input, model_type, system_prompt, role_id
            )

            # 步骤2: 获取模型客户端并开始流式生成
            model_client = ModelService.get_model_client(model_type, model_params)
            full_response = ""

            import json as _json
            for chunk in model_client.stream(messages):
                full_response += chunk
                # 以 SSE 格式推送每个数据块: "data: <json>\n\n"
                yield f"data: {_json.dumps(chunk)}\n\n"

            # 步骤3: 将原始消息（不包含文件内容）保存到数据库
            # 附件信息通过消息文本前标注的方式体现
            display_msg = original_message
            if attach_filename:
                display_msg = '📎 '+attach_filename+'\n'+original_message
            Message.create(conversation.id, "user", display_msg)
            Message.create(conversation.id, "assistant", full_response)

            # 步骤4: 若是新建会话（标题为"新对话"），
            # 自动根据用户的第一条输入生成会话标题
            if conversation.title == "新对话":
                conversation.title = user_input[:30] + ("..." if len(user_input) > 30 else "")
                from app.extensions import db
                db.session.commit()

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
