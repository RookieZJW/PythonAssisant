from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from .base import BaseLLMClient


class DeepSeekClient(BaseLLMClient):
    """DeepSeek 模型客户端"""

    def __init__(self, api_key: str, model: str = "deepseek-chat",
                 temperature: float = 0.7, max_tokens: int = 2048):
        self._model_name = model
        self.model = ChatDeepSeek(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True
        )

    def invoke(self, messages: list, **kwargs) -> str:
        lc_messages = self._convert_messages(messages)
        response = self.model.invoke(lc_messages, **kwargs)
        return response.content

    async def ainvoke(self, messages: list, **kwargs) -> str:
        lc_messages = self._convert_messages(messages)
        response = await self.model.ainvoke(lc_messages, **kwargs)
        return response.content

    def stream(self, messages: list, **kwargs):
        lc_messages = self._convert_messages(messages)
        for chunk in self.model.stream(lc_messages, **kwargs):
            yield chunk.content

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
