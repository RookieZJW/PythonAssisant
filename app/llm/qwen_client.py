from langchain_community.llms import Tongyi
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from .base import BaseLLMClient


class QwenClient(BaseLLMClient):
    """通义千问模型客户端"""

    def __init__(self, api_key: str, model: str = "qwen-plus",
                 temperature: float = 0.7, max_tokens: int = 2048):
        self._model_name = model
        self.model = Tongyi(
            model=model,
            dashscope_api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def invoke(self, messages: list, **kwargs) -> str:
        lc_messages = self._convert_messages(messages)
        response = self.model.invoke(lc_messages, **kwargs)
        return response

    async def ainvoke(self, messages: list, **kwargs) -> str:
        lc_messages = self._convert_messages(messages)
        response = await self.model.ainvoke(lc_messages, **kwargs)
        return response

    def stream(self, messages: list, **kwargs):
        lc_messages = self._convert_messages(messages)
        for chunk in self.model.stream(lc_messages, **kwargs):
            yield chunk

    def get_model_name(self) -> str:
        return self._model_name

    def _convert_messages(self, messages: list) -> list:
        """将标准消息格式转换为 LangChain 消息格式"""
        mapping = {
            "system": SystemMessage,
            "user": HumanMessage,
            "assistant": AIMessage
        }
        return [
            mapping[msg["role"]](content=msg["content"])
            for msg in messages
            if msg.get("role") in mapping
        ]
