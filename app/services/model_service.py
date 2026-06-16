from app.llm.deepseek_client import DeepSeekClient
from app.llm.qwen_client import QwenClient
from app.config.settings import settings


class ModelService:
    """模型调度服务

    使用工厂模式管理不同模型客户端实例，支持根据用户请求动态选择模型。
    """

    _instances = {}

    @classmethod
    def get_model_client(cls, model_type: str = None):
        """获取指定模型客户端，默认使用配置中的默认模型"""
        model_type = model_type or settings.DEFAULT_MODEL

        if model_type not in cls._instances:
            if model_type == "deepseek":
                cls._instances[model_type] = DeepSeekClient(
                    api_key=settings.DEEPSEEK_API_KEY,
                    model=settings.DEEPSEEK_MODEL,
                    temperature=settings.TEMPERATURE,
                    max_tokens=settings.MAX_TOKENS
                )
            elif model_type == "qwen":
                cls._instances[model_type] = QwenClient(
                    api_key=settings.QWEN_API_KEY,
                    model=settings.QWEN_MODEL,
                    temperature=settings.TEMPERATURE,
                    max_tokens=settings.MAX_TOKENS
                )
            else:
                raise ValueError(f"不支持的模型类型: {model_type}")

        return cls._instances[model_type]

    @classmethod
    def get_available_models(cls) -> list:
        """获取可用模型列表"""
        models = []
        if settings.DEEPSEEK_API_KEY:
            models.append({
                "name": "deepseek",
                "display_name": "DeepSeek",
                "model": settings.DEEPSEEK_MODEL,
            })
        if settings.QWEN_API_KEY:
            models.append({
                "name": "qwen",
                "display_name": "通义千问",
                "model": settings.QWEN_MODEL,
            })
        return models
