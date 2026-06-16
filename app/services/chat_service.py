from .model_service import ModelService
from app.llm.memory import ConversationMemory
from app.models.conversation import Conversation
from app.models.message import Message
from app.config.settings import settings


class ChatService:
    """对话服务

    封装对话核心业务逻辑流程:
    1. 获取或创建会话
    2. 加载对话历史
    3. 组装消息列表
    4. 调用大模型
    5. 持久化消息记录
    """

    @staticmethod
    def chat(conversation_id: str, user_input: str,
             model_type: str = None, system_prompt: str = None):
        """同步对话接口"""
        # 1. 获取或创建会话
        conversation = Conversation.get_or_create(conversation_id)

        # 2. 初始化记忆并加载历史
        memory = ConversationMemory(conversation.id, k=10)
        history_messages = Message.get_history(conversation.id, limit=20)
        memory.load_history(history_messages)

        # 3. 组装消息
        messages = []
        if system_prompt or settings.DEFAULT_SYSTEM_PROMPT:
            messages.append({
                "role": "system",
                "content": system_prompt or settings.DEFAULT_SYSTEM_PROMPT
            })
        messages.extend(memory.get_messages())
        messages.append({"role": "user", "content": user_input})

        # 4. 调用模型
        model_client = ModelService.get_model_client(model_type)
        response = model_client.invoke(messages)

        # 5. 持久化存储
        Message.create(conversation.id, "user", user_input)
        Message.create(conversation.id, "assistant", response)

        # 6. 更新会话标题（使用第一条用户消息）
        if conversation.title == "新对话":
            conversation.title = user_input[:30] + ("..." if len(user_input) > 30 else "")
            from app.extensions import db
            db.session.commit()

        return {
            "conversation_id": conversation.id,
            "answer": response,
            "model": model_client.get_model_name(),
        }

    @staticmethod
    def prepare_chat_context(conversation_id: str, user_input: str,
                             model_type: str = None, system_prompt: str = None):
        """准备对话上下文（供流式接口使用）"""
        conversation = Conversation.get_or_create(conversation_id)
        memory = ConversationMemory(conversation.id, k=10)
        history_messages = Message.get_history(conversation.id, limit=20)
        memory.load_history(history_messages)

        messages = []
        if system_prompt or settings.DEFAULT_SYSTEM_PROMPT:
            messages.append({
                "role": "system",
                "content": system_prompt or settings.DEFAULT_SYSTEM_PROMPT
            })
        messages.extend(memory.get_messages())
        messages.append({"role": "user", "content": user_input})

        return conversation, memory, messages
