from langchain_classic.memory import ConversationBufferWindowMemory

# LangChain 1.x: 移除了 messages_from_dict，直接使用字典列表即可


class ConversationMemory:
    """对话记忆管理器

    基于 LangChain 的 ConversationBufferWindowMemory 实现滑动窗口记忆，
    结合数据库持久化，支持历史消息的加载与保存。
    """

    def __init__(self, conversation_id: str, k: int = 10):
        self.conversation_id = conversation_id
        self.k = k  # 只保留最近 k 轮对话
        self.memory = ConversationBufferWindowMemory(
            k=k,
            return_messages=True,
            memory_key="chat_history"
        )

    def load_history(self, messages: list):
        """从数据库加载历史消息并载入内存"""
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                self.memory.chat_memory.add_user_message(content)
            elif role == "assistant":
                self.memory.chat_memory.add_ai_message(content)

    def add_user_message(self, content: str):
        """添加用户消息到记忆"""
        self.memory.chat_memory.add_user_message(content)

    def add_ai_message(self, content: str):
        """添加 AI 消息到记忆"""
        self.memory.chat_memory.add_ai_message(content)

    def get_messages(self) -> list:
        """获取格式化后的消息列表"""
        history = self.memory.load_memory_variables({})["chat_history"]
        messages = []
        for msg in history:
            role = "user" if msg.type == "human" else "assistant"
            messages.append({"role": role, "content": msg.content})
        return messages
