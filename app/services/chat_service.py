# =============================================================================
# 对话服务模块 (Chat Service)
# =============================================================================
# 本模块提供对话系统的核心业务逻辑封装，包括：
#   - 会话的获取与创建
#   - 对话历史的加载与管理
#   - 消息列表的组装与格式转换
#   - 大语言模型的同步/流式调用
#   - 消息记录的持久化存储
#   - 会话标题的自动生成
# =============================================================================

from .model_service import ModelService
from app.llm.memory import ConversationMemory
from app.models.conversation import Conversation
from app.models.message import Message
from app.config.settings import settings


class ChatService:
    """对话服务

    封装对话核心业务逻辑流程:
    1. 获取或创建会话 —— 根据传入的会话ID查找已有会话，若不存在则新建
    2. 加载对话历史 —— 从数据库读取历史消息并载入记忆管理器
    3. 组装消息列表 —— 将系统提示词、历史消息、当前用户输入拼接为完整的消息列表
    4. 调用大模型 —— 通过模型客户端工厂获取对应的模型实例并发送请求
    5. 持久化消息记录 —— 将用户消息和模型回复保存到数据库
    6. 更新会话标题 —— 使用第一条用户消息的前30个字符作为会话标题

    该类设计为纯静态方法集合（无实例状态），简化调用方式。
    """

    @staticmethod
    def chat(conversation_id: str, user_input: str,
             model_type: str = None, system_prompt: str = None,
             role_id: str = None):
        """同步对话接口 —— 完整的对话请求-响应流程

        参数:
            conversation_id (str): 会话唯一标识符（UUID字符串）
            user_input (str): 用户输入的文本内容
            model_type (str, optional): 模型类型标识，如 "deepseek" 或 "qwen"。
                为 None 时使用 settings 中的默认配置。
            system_prompt (str, optional): 系统提示词，用于设定模型行为角色。
                为 None 时使用全局默认系统提示词。
            role_id (str, optional): 角色/人格ID，用于绑定特定角色设定。
                仅在首次创建会话时生效。

        返回:
            dict: 包含以下字段的响应字典：
                - conversation_id (str): 会话ID
                - answer (str): 模型生成的回复文本
                - model (str): 实际使用的模型名称

        工作流程:
            1. 获取或创建会话（首次创建时绑定角色）
            2. 初始化对话记忆并加载历史消息（最多20条）
            3. 组装消息列表（系统提示词 + 历史消息 + 当前输入）
            4. 通过模型服务获取对应模型客户端并调用
            5. 将用户消息和模型回复持久化到数据库
            6. 若为新对话则自动生成标题（取第一条消息前30字）
        """
        # 1. 获取或创建会话（首次创建时绑定角色）
        conversation = Conversation.get_or_create(conversation_id, role_id=role_id)

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
                             model_type: str = None, system_prompt: str = None,
                             role_id: str = None):
        """准备对话上下文（供流式接口使用）

        该方法是 chat() 的前半部分拆分，用于流式（SSE）场景：
        调用方先通过此方法获取会话对象、记忆管理器和组装好的消息列表，
        然后自行处理模型的流式调用和消息持久化。

        参数:
            conversation_id (str): 会话唯一标识符
            user_input (str): 用户输入的文本内容
            model_type (str, optional): 模型类型标识
            system_prompt (str, optional): 系统提示词
            role_id (str, optional): 角色/人格ID

        返回:
            tuple: (conversation, memory, messages)
                - conversation (Conversation): 会话 ORM 对象
                - memory (ConversationMemory): 对话记忆管理器实例
                - messages (list): 组装完成的消息列表，格式为
                  [{"role": "system"|"user"|"assistant", "content": str}, ...]
        """
        conversation = Conversation.get_or_create(conversation_id, role_id=role_id)
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
