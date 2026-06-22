# =============================================================================
# 对话记忆管理模块 (Conversation Memory)
# =============================================================================
# 本模块实现了基于滑动窗口（Sliding Window）的对话记忆管理器，
# 用于在对话过程中维护短期上下文，避免超出模型的上下文窗口限制。
#
# 设计要点：
#   1. 基于 LangChain 的 ConversationBufferWindowMemory 实现底层存储
#   2. 滑动窗口机制：仅保留最近 k 轮对话，自动丢弃旧消息
#   3. 数据库双向同步：支持从数据库加载历史消息，也可动态添加新消息
#   4. 统一消息格式：与系统其他部分使用相同的 {"role": ..., "content": ...} 格式
#
# 工作流程：
#   1. 初始化时指定会话 ID 和窗口大小 k
#   2. 从数据库加载历史消息到记忆缓冲区
#   3. 在对话过程中持续添加新消息
#   4. 获取格式化后的消息列表供模型调用使用
# =============================================================================

from langchain_classic.memory import ConversationBufferWindowMemory


class ConversationMemory:
    """对话记忆管理器

    基于 LangChain 的 ConversationBufferWindowMemory 实现滑动窗口记忆，
    结合数据库持久化，支持历史消息的加载与保存。

    滑动窗口机制：
        只保留最近 k 轮（用户+助手为一轮）对话在内存中，
        超出窗口的旧消息被自动丢弃，确保记忆不会无限增长。
        这可以控制发送给大模型的上下文长度，避免超出 Token 限制。

    使用示例:
        >>> memory = ConversationMemory("conv_123", k=10)
        >>> history = Message.get_history("conv_123", limit=20)
        >>> memory.load_history(history)
        >>> memory.add_user_message("你好")
        >>> memory.add_ai_message("你好！有什么可以帮助你的？")
        >>> messages = memory.get_messages()
    """

    def __init__(self, conversation_id: str, k: int = 10):
        """初始化对话记忆管理器

        参数:
            conversation_id (str): 会话唯一标识符，用于关联数据库中的会话记录
            k (int, optional): 滑动窗口大小，表示保留的最近对话轮次数量。
                默认值为 10，即保留最近 10 轮（共 20 条）消息。
                每轮包含一条用户消息和一条 AI 回复。
        """
        self.conversation_id = conversation_id
        self.k = k  # 只保留最近 k 轮对话
        # 初始化 LangChain 的对话缓冲区窗口记忆组件
        # return_messages=True 使 load_memory_variables 返回消息对象列表而非纯字符串
        # memory_key 是 LangChain 内部使用的变量名，用于标识对话历史
        self.memory = ConversationBufferWindowMemory(
            k=k,
            return_messages=True,
            memory_key="chat_history"
        )

    def load_history(self, messages: list):
        """从数据库加载历史消息并载入内存

        将数据库查询到的历史消息逐一注入到记忆管理器中。
        该方法根据消息的 role 字段决定添加到用户方还是 AI 方。

        参数:
            messages (list): 历史消息列表，每条消息为字典格式
                [{"role": "user"|"assistant", "content": str, ...}, ...]
                通常来自 Message.get_history() 的查询结果。
        """
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                # 添加到用户消息缓冲区
                self.memory.chat_memory.add_user_message(content)
            elif role == "assistant":
                # 添加到 AI 消息缓冲区
                self.memory.chat_memory.add_ai_message(content)

    def add_user_message(self, content: str):
        """添加用户消息到记忆

        在对话过程中动态添加新的用户消息，
        自动维护滑动窗口（超出 k 轮的旧消息会被丢弃）。

        参数:
            content (str): 用户发送的消息文本内容
        """
        self.memory.chat_memory.add_user_message(content)

    def add_ai_message(self, content: str):
        """添加 AI 消息到记忆

        在对话过程中动态添加新的 AI 回复，
        与 add_user_message 成对使用以维护完整的对话轮次。

        参数:
            content (str): AI 模型生成的回复文本内容
        """
        self.memory.chat_memory.add_ai_message(content)

    def get_messages(self) -> list:
        """获取格式化后的消息列表

        从记忆管理器中提取当前缓冲区中的消息，
        转换为系统统一的字典格式供模型调用使用。

        转换过程：
            1. 调用 LangChain 的 load_memory_variables({}) 获取原始消息对象列表
            2. 遍历消息对象，根据 msg.type 判断消息角色
            3. 组装为 {"role": role, "content": content} 字典格式

        返回:
            list: 格式化后的消息字典列表，格式为
                [{"role": "user"|"assistant", "content": str}, ...]
                注意：系统提示词（system role）不在此列表中，
                由 ChatService 在组装消息列表时单独添加。

        角色映射:
            LangChain msg.type == "human"   -> role = "user"
            LangChain msg.type == "ai"      -> role = "assistant"
        """
        history = self.memory.load_memory_variables({})["chat_history"]
        messages = []
        for msg in history:
            role = "user" if msg.type == "human" else "assistant"
            messages.append({"role": role, "content": msg.content})
        return messages
