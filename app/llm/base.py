# =============================================================================
# 大语言模型客户端抽象基类模块 (Base LLM Client)
# =============================================================================
# 本模块定义了所有大语言模型（LLM）客户端的抽象基类 BaseLLMClient，
# 采用策略模式（Strategy Pattern）结合工厂模式（Factory Pattern）设计。
#
# 设计目标：
#   1. 统一接口：为所有模型客户端定义一致的调用契约
#   2. 策略可替换：不同模型厂商（DeepSeek、通义千问等）各自实现具体客户端
#   3. 多范式支持：同步调用、异步调用、流式调用三种交互模式
#   4. 扩展友好：新增模型厂商只需继承本类并实现所有抽象方法
#
# 接口规范：
#   所有子类必须实现以下四个方法：
#   - invoke()      : 同步调用，适用于简单请求-响应场景
#   - ainvoke()     : 异步调用，适用于高并发场景
#   - stream()      : 流式调用，适用于逐 token 输出场景（如打字机效果）
#   - get_model_name(): 获取当前使用的模型名称
# =============================================================================

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict


class BaseLLMClient(ABC):
    """大模型客户端抽象基类

    使用策略模式 + 工厂模式，通过统一的抽象类定义模型调用接口，
    不同模型厂商各自实现具体客户端。

    继承该类时必须实现的方法:
        - invoke(self, messages, **kwargs) -> str
            同步发送消息列表并获取完整回复
        - ainvoke(self, messages, **kwargs) -> str
            异步发送消息列表并获取完整回复
        - stream(self, messages, **kwargs) -> Generator
            流式发送消息列表并逐块获取回复内容
        - get_model_name(self) -> str
            返回当前模型的具体名称/版本标识

    消息格式约定:
        messages 参数应为列表，每个元素为字典，包含:
            - "role" (str): "system" | "user" | "assistant"
            - "content" (str): 消息文本内容
    """

    @abstractmethod
    def invoke(self, messages: List[Dict], **kwargs) -> str:
        """同步调用接口

        发送完整的消息列表到模型，等待模型生成完整的回复后返回。

        参数:
            messages (List[Dict]): 消息列表，格式为
                [{"role": "system"|"user"|"assistant", "content": str}, ...]
            **kwargs: 额外的调用参数（如 temperature、top_p 等运行时参数）

        返回:
            str: 模型生成的完整回复文本
        """
        pass

    @abstractmethod
    async def ainvoke(self, messages: List[Dict], **kwargs) -> str:
        """异步调用接口

        异步版本的 invoke()，适用于需要并发处理多个请求的场景。
        使用 asyncio 异步 IO 避免线程阻塞，提升系统吞吐量。

        参数:
            messages (List[Dict]): 消息列表，格式同 invoke() 方法
            **kwargs: 额外的调用参数

        返回:
            str: 模型生成的完整回复文本
        """
        pass

    @abstractmethod
    def stream(self, messages: List[Dict], **kwargs) -> object:
        """流式调用接口

        以生成器（Generator）的形式逐块返回模型输出，适用于：
        - 实时展示 AI 打字机效果（SSE）
        - 处理长回复时减少用户等待时间
        - 需要提前展示部分结果的场景

        参数:
            messages (List[Dict]): 消息列表，格式同 invoke() 方法
            **kwargs: 额外的调用参数

        返回:
            Generator 或 可迭代对象: 逐块产出模型生成的文本片段，
                调用方可通过迭代逐个处理每个 token 或文本块
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """获取模型名称

        返回当前客户端配置的具体模型版本标识，
        用于日志记录、前端展示和费用统计。

        返回:
            str: 模型名称字符串，如 "deepseek-chat"、"qwen-plus" 等
        """
        pass
