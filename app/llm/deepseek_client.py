# =============================================================================
# DeepSeek 模型客户端模块 (DeepSeek Client)
# =============================================================================
# 本模块实现了针对 DeepSeek 大语言模型的客户端封装，
# 通过 langchain-deepseek 集成库与 DeepSeek API 进行通信。
#
# DeepSeek 模型特点：
#   - 支持中英文双语，中文场景表现优异
#   - 支持流式输出（streaming=True）
#   - 兼容 OpenAI API 格式
#
# 继承关系：
#   BaseLLMClient (抽象基类)
#       └── DeepSeekClient (本类, 具体实现)
#
# 关键依赖：
#   - langchain_deepseek.ChatDeepSeek: LangChain 官方 DeepSeek 集成
#   - langchain_core.messages: 消息类型转换工具
# =============================================================================

from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from .base import BaseLLMClient


class DeepSeekClient(BaseLLMClient):
    """DeepSeek 模型客户端

    继承自 BaseLLMClient 抽象基类，实现 DeepSeek 大模型的具体调用逻辑。
    内部使用 langchain_deepseek.ChatDeepSeek 作为实际调用引擎，
    通过统一的消息格式转换接口保持与系统其他部分的兼容性。

    支持的模型版本（通过 model 参数指定）:
        - "deepseek-chat": DeepSeek-V3 聊天模型（默认）
        - "deepseek-reasoner": DeepSeek-R1 推理模型（如有需要）
    """

    def __init__(self, api_key: str, model: str = "deepseek-chat",
                 temperature: float = 0.7, max_tokens: int = 2048):
        """初始化 DeepSeek 客户端

        参数:
            api_key (str): DeepSeek API 密钥，从 settings 配置文件获取
            model (str, optional): 模型名称，默认为 "deepseek-chat"
            temperature (float, optional): 生成温度参数，控制输出的随机性。
                取值范围 0.0~2.0，值越高输出越随机多样。默认为 0.7。
            max_tokens (int, optional): 单次生成的最大 Token 数量。
                限制模型回复的最大长度。默认为 2048。
        """
        self._model_name = model
        # 初始化 LangChain 封装的 DeepSeek 聊天模型实例
        # streaming=True 启用流式输出能力，支持 stream() 方法
        self.model = ChatDeepSeek(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True
        )

    def invoke(self, messages: list, **kwargs) -> str:
        """同步调用 DeepSeek 模型

        将应用层消息格式转换为 LangChain 消息格式后调用模型，
        返回完整的回复文本。

        参数:
            messages (list): 标准消息列表，格式为
                [{"role": "system"|"user"|"assistant", "content": str}, ...]
            **kwargs: 传递给底层 ChatDeepSeek.invoke() 的额外参数

        返回:
            str: 模型生成的完整回复内容（字符串）
        """
        lc_messages = self._convert_messages(messages)
        response = self.model.invoke(lc_messages, **kwargs)
        return response.content

    async def ainvoke(self, messages: list, **kwargs) -> str:
        """异步调用 DeepSeek 模型

        异步版本的 invoke()，使用 asyncio 事件循环避免阻塞主线程。

        参数:
            messages (list): 标准消息列表，格式同 invoke()
            **kwargs: 传递给底层 ChatDeepSeek.ainvoke() 的额外参数

        返回:
            str: 模型生成的完整回复内容（字符串）
        """
        lc_messages = self._convert_messages(messages)
        response = await self.model.ainvoke(lc_messages, **kwargs)
        return response.content

    def stream(self, messages: list, **kwargs):
        """流式调用 DeepSeek 模型

        以生成器（Generator）形式逐块产出模型输出的文本片段。
        每块通常对应一个或几个 token，适用于实现打字机效果。

        参数:
            messages (list): 标准消息列表，格式同 invoke()
            **kwargs: 传递给底层 ChatDeepSeek.stream() 的额外参数

        生成器产出:
            str: 每轮迭代产出一个文本片段（chunk.content），
                调用方可通过 for chunk in client.stream(...) 迭代处理
        """
        lc_messages = self._convert_messages(messages)
        for chunk in self.model.stream(lc_messages, **kwargs):
            yield chunk.content

    def get_model_name(self) -> str:
        """获取当前 DeepSeek 模型名称

        返回:
            str: 构造函数中传入的 model 参数值，如 "deepseek-chat"
        """
        return self._model_name

    def _convert_messages(self, messages: list) -> list:
        """将标准消息格式转换为 LangChain 消息格式

        应用层使用统一的字典格式表示消息：
            {"role": "system"|"user"|"assistant", "content": "..."}

        LangChain 使用不同类型的对象表示消息：
            - SystemMessage: 系统提示词
            - HumanMessage: 用户消息
            - AIMessage: 模型回复

        本方法通过角色映射表实现格式转换，
        忽略 roles 映射表中不存在的消息角色（如 "tool" 等）。

        参数:
            messages (list): 标准字典格式的消息列表

        返回:
            list: LangChain 消息对象列表，元素类型为
                SystemMessage | HumanMessage | AIMessage

        消息角色映射表:
            "system"    -> SystemMessage
            "user"      -> HumanMessage
            "assistant" -> AIMessage
        """
        # 定义角色到 LangChain 消息类的映射关系
        mapping = {
            "system": SystemMessage,
            "user": HumanMessage,
            "assistant": AIMessage
        }
        # 遍历消息列表，对每条消息进行格式转换
        # 通过 mapping.get() 确保只处理已知角色，未知角色被跳过
        return [
            mapping[msg["role"]](content=msg["content"])
            for msg in messages
            if msg.get("role") in mapping
        ]
