# =============================================================================
# 模型调度服务模块 (Model Service)
# =============================================================================
# 本模块使用工厂模式管理不同大语言模型（LLM）客户端的实例创建与缓存，
# 支持根据用户请求动态选择模型提供商，并允许通过参数覆盖默认配置。
#
# 设计要点：
#   - 类级别缓存（_instances 字典）：无自定义参数时复用已创建的客户端实例
#   - 自定义参数时每次创建新实例，避免配置污染
#   - 通过配置文件（settings）集中管理 API Key 和模型版本
# =============================================================================

from app.llm.deepseek_client import DeepSeekClient
from app.llm.qwen_client import QwenClient
from app.config.settings import settings


class ModelService:
    """模型调度服务

    使用工厂模式管理不同模型客户端实例，支持根据用户请求动态选择模型。
    核心职责：
    1. 根据模型类型标识（字符串）创建对应的客户端实例
    2. 合并默认配置与用户自定义参数
    3. 通过缓存机制减少不必要的实例创建
    4. 提供可用模型列表查询功能

    当前支持的模型类型：
        - "deepseek" -> DeepSeekClient（DeepSeek 大模型）
        - "qwen"     -> QwenClient（通义千问大模型）
    """

    _instances = {}
    """类级别缓存字典：键为模型类型字符串，值为对应的客户端实例。
    当没有自定义参数传入时，优先从缓存中获取已创建的实例以复用连接资源。"""

    @classmethod
    def get_model_client(cls, model_type: str = None, params: dict = None):
        """获取模型客户端，支持动态参数覆盖

        参数:
            model_type (str, optional): 模型类型标识，可选值 "deepseek" | "qwen"。
                为 None 时使用 settings.DEFAULT_MODEL 的默认值。
            params (dict, optional): 自定义参数字典，可覆盖以下配置项：
                - temperature (float): 生成温度，控制输出的随机性，默认为 settings.TEMPERATURE
                - max_tokens (int): 最大生成 Token 数，默认为 settings.MAX_TOKENS
                - top_p (float): 核采样参数，默认为 1.0

        返回:
            BaseLLMClient: 模型客户端实例（DeepSeekClient 或 QwenClient），
                实现了 BaseLLMClient 抽象基类的 invoke/ainvoke/stream 等方法。

        抛出:
            ValueError: 当 model_type 不是支持的模型类型时抛出

        工作流程:
            1. 将 model_type 设为默认值（若为 None）
            2. 合并参数：将传入的自定义参数与默认配置合并
            3. 判断是否有自定义参数：
               - 有自定义参数 -> 每次都创建新实例（避免配置混淆）
               - 无自定义参数 -> 优先使用缓存实例，不存在时创建并缓存
            4. 根据 model_type 选择对应的客户端类
            5. 使用合并后的参数调用客户端构造函数
        """
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
        """获取可用模型列表

        根据配置文件中是否配置了对应的 API Key 来动态决定哪些模型可用。
        这样可以优雅降级 —— 用户只需配置一个模型时，系统不会展示不可用的选项。

        返回:
            list: 可用模型信息的字典列表，每个字典包含：
                - name (str): 模型内部标识名，如 "deepseek"
                - display_name (str): 模型展示名，如 "DeepSeek" / "通义千问"
                - model (str): 具体模型版本名，如 "deepseek-chat" / "qwen-plus"
        """
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
