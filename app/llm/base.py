from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict


class BaseLLMClient(ABC):
    """大模型客户端抽象基类

    使用策略模式 + 工厂模式，通过统一的抽象类定义模型调用接口，
    不同模型厂商各自实现具体客户端。
    """

    @abstractmethod
    def invoke(self, messages: List[Dict], **kwargs) -> str:
        """同步调用"""
        pass

    @abstractmethod
    async def ainvoke(self, messages: List[Dict], **kwargs) -> str:
        """异步调用"""
        pass

    @abstractmethod
    def stream(self, messages: List[Dict], **kwargs) -> object:
        """流式调用，返回生成器"""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """获取模型名称"""
        pass
