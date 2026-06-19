from flask import Blueprint, request, Response, stream_with_context
from app.services.chat_service import ChatService
from app.services.model_service import ModelService
from app.models.conversation import Conversation
from app.models.message import Message
from app.llm.memory import ConversationMemory
from app.config.settings import settings
from app.utils.response import success, error

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chat', methods=['POST'])
def chat():
    """普通对话接口（同步）"""
    data = request.get_json()
    if not data or 'message' not in data:
        return error("message 参数不能为空", 400)

    try:
        result = ChatService.chat(
            conversation_id=data.get('conversation_id', 'default'),
            user_input=data['message'],
            model_type=data.get('model'),
            system_prompt=data.get('system_prompt'),
            role_id=data.get('role_id'),
        )
        return success(result)
    except ValueError as e:
        return error(str(e), 400)
    except Exception as e:
        return error(f"对话失败: {str(e)}", 500)


@chat_bp.route('/chat/stream', methods=['POST'])
def chat_stream():
    """流式对话接口（SSE）"""
    data = request.get_json()
    if not data or 'message' not in data:
        return error("message 参数不能为空", 400)

    conversation_id = data.get('conversation_id', 'default')
    original_message = data['message']  # 用户原始输入（存数据库）
    user_input = original_message
    model_type = data.get('model')
    system_prompt = data.get('system_prompt')
    role_id = data.get('role_id')
    model_params = data.get('params', {})
    attachment = data.get('attachment', {})
    attach_filename = ''

    # 有附件时，拼文件内容到 LLM 上下文（但不存数据库）
    if attachment and attachment.get('content'):
        attach_filename = attachment.get('filename', '文件')
        file_ctx = f"[用户上传了文件: {attach_filename}]\n\n文件内容:\n```\n{attachment['content']}\n```\n\n基于以上文件内容，回答用户问题:\n"
        user_input = file_ctx + original_message

    def generate():
        try:
            conversation, memory, messages = ChatService.prepare_chat_context(
                conversation_id, user_input, model_type, system_prompt, role_id
            )

            model_client = ModelService.get_model_client(model_type, model_params)
            full_response = ""

            import json as _json
            for chunk in model_client.stream(messages):
                full_response += chunk
                yield f"data: {_json.dumps(chunk)}\n\n"

            # 存原始消息（不含文件内容），附件信息通过 role 前缀标注
            display_msg = original_message
            if attach_filename:
                display_msg = '📎 '+attach_filename+'\n'+original_message
            Message.create(conversation.id, "user", display_msg)
            Message.create(conversation.id, "assistant", full_response)

            # 更新标题
            if conversation.title == "新对话":
                conversation.title = user_input[:30] + ("..." if len(user_input) > 30 else "")
                from app.extensions import db
                db.session.commit()

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )
