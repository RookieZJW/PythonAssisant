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
    user_input = data['message']
    model_type = data.get('model')
    system_prompt = data.get('system_prompt')
    role_id = data.get('role_id')
    model_params = data.get('params', {})  # {temperature, max_tokens, top_p}

    def generate():
        try:
            conversation, memory, messages = ChatService.prepare_chat_context(
                conversation_id, user_input, model_type, system_prompt, role_id
            )

            # 调用模型流式输出（支持参数覆盖）
            model_client = ModelService.get_model_client(model_type, model_params)
            full_response = ""

            import json as _json
            for chunk in model_client.stream(messages):
                full_response += chunk
                yield f"data: {_json.dumps(chunk)}\n\n"

            # 持久化
            Message.create(conversation.id, "user", user_input)
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
