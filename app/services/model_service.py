from app.llm.deepseek_client import DeepSeekClient
from app.llm.qwen_client import QwenClient
from app.config.settings import settings


class ModelService:
    """模型调度服务

    使用工厂模式管理不同模型客户端实例，支持根据用户请求动态选择模型。
    """

    _instances = {}

    @classmethod
    def get_model_client(cls, model_type: str = None, params: dict = None):
        """获取模型客户端，支持动态参数覆盖"""
        model_type = model_type or settings.DEFAULT_MODEL
        params = params or {}

        # 合并配置：默认值 + 用户覆盖
        temperature = float(params.get('temperature', settings.TEMPERATURE))
        max_tokens = int(params.get('max_tokens', settings.MAX_TOKENS))
        top_p = float(params.get('top_p', 1.0))

        # 有自定义参数时创建新实例（不走缓存）
        if params:
            if model_type == "deepseek":
                return DeepSeekClient(
                    api_key=settings.DEEPSEEK_API_KEY,
                    model=settings.DEEPSEEK_MODEL,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            elif model_type == "qwen":
                return QwenClient(
                    api_key=settings.QWEN_API_KEY,
                    model=settings.QWEN_MODEL,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            else:
                raise ValueError(f"不支持的模型类型: {model_type}")

        # 无自定义参数走缓存
        if model_type not in cls._instances:
            if model_type == "deepseek":
                cls._instances[model_type] = DeepSeekClient(
                    api_key=settings.DEEPSEEK_API_KEY,
                    model=settings.DEEPSEEK_MODEL,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            elif model_type == "qwen":
                cls._instances[model_type] = QwenClient(
                    api_key=settings.QWEN_API_KEY,
                    model=settings.QWEN_MODEL,
                    temperature=temperature,
                    max_tokens=max_tokens
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
