import os
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    """基础配置"""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 大模型通用配置
    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", 2048))
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek")
    DEFAULT_SYSTEM_PROMPT = "你是一个智能助手，请用简洁准确的语言回答用户的问题。"

    # DeepSeek 配置
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # 通义千问配置
    QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
    QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")

    # 火山引擎 TTS 配置（可选）
    VOLCANO_TTS_APP_ID = os.getenv("VOLCANO_TTS_APP_ID", "")
    VOLCANO_TTS_TOKEN = os.getenv("VOLCANO_TTS_TOKEN", "")

    # 腾讯云 TTS 配置（可选）
    TENCENT_TTS_SECRET_ID = os.getenv("TENCENT_TTS_SECRET_ID", "")
    TENCENT_TTS_SECRET_KEY = os.getenv("TENCENT_TTS_SECRET_KEY", "")

    # Redis 配置
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # 限流配置
    RATE_LIMIT = int(os.getenv("RATE_LIMIT", 60))

    # MySQL 引擎配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
        "echo": False,
    }


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "mysql+pymysql://root:Zhang20.@localhost:3306/smart_assistant")


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "mysql+pymysql://root:Zhang20.@localhost:3306/smart_assistant")


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

settings = config[os.getenv("FLASK_ENV", "development")]
