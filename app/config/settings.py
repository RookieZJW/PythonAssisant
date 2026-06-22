"""
全局配置文件
=============
这个文件负责从 .env 文件中加载所有配置项, 并根据 FLASK_ENV 环境变量
选择对应的配置类 (开发/生产/测试), 最终暴露一个 settings 对象供整个项目使用。

配置分层:
  BaseConfig       → 公共配置 (所有环境共享)
  DevelopmentConfig → 开发环境 (DEBUG=True, 本地 MySQL)
  ProductionConfig  → 生产环境 (DEBUG=False)
  TestingConfig     → 测试环境 (SQLite 内存数据库)
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量 (API Key, 数据库密码等敏感信息不应写在代码里)
load_dotenv()


class BaseConfig:
    """基础配置 —— 所有环境的公共默认值"""

    # ===== Flask 核心 =====
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")  # 密钥 (生产环境务必更换!)
    SQLALCHEMY_TRACK_MODIFICATIONS = False                  # 关闭 SQLAlchemy 的修改追踪 (省内存)

    # ===== 大模型通用参数 =====
    TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))      # 模型温度 (0=严谨, 1=创意, 2=狂野)
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", 2048))          # 单次回复最大 Token 数
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek")   # 默认使用哪个模型 (deepseek / qwen)
    DEFAULT_SYSTEM_PROMPT = "你是一个智能助手，请用简洁准确的语言回答用户的问题。"

    # ===== DeepSeek 配置 =====
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # ===== 通义千问配置 =====
    QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
    QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")

    # ===== 火山引擎 TTS 配置 (语音合成, 可选) =====
    VOLCANO_TTS_APP_ID = os.getenv("VOLCANO_TTS_APP_ID", "")
    VOLCANO_TTS_TOKEN = os.getenv("VOLCANO_TTS_TOKEN", "")

    # ===== 腾讯云 TTS 配置 (语音合成, 可选) =====
    TENCENT_TTS_SECRET_ID = os.getenv("TENCENT_TTS_SECRET_ID", "")
    TENCENT_TTS_SECRET_KEY = os.getenv("TENCENT_TTS_SECRET_KEY", "")

    # ===== Redis 配置 (限流用, 可选) =====
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ===== 限流配置 =====
    RATE_LIMIT = int(os.getenv("RATE_LIMIT", 60))  # 每 IP 每分钟最多请求次数

    # ===== MySQL 连接池配置 =====
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,           # 连接池大小 (同时保持 10 个数据库连接)
        "pool_recycle": 3600,      # 连接回收时间 (1 小时后自动重连, 防止 MySQL 断开)
        "pool_pre_ping": True,     # 每次使用前先 ping 一下 (确保连接还活着)
        "echo": False,             # 不打印 SQL 日志 (调试时可设为 True)
    }


class DevelopmentConfig(BaseConfig):
    """开发环境配置"""
    DEBUG = True
    # 数据库连接: mysql+pymysql://用户名:密码@地址:端口/数据库名
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:Zhang20.@localhost:3306/smart_assistant"
    )


class ProductionConfig(BaseConfig):
    """生产环境配置"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:Zhang20.@localhost:3306/smart_assistant"
    )


class TestingConfig(BaseConfig):
    """测试环境配置 —— 使用 SQLite 内存数据库 (速度快, 不落盘)"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


# ---- 根据 FLASK_ENV 选择配置类 ----
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

# 最终暴露的 settings 对象 —— 项目中所有地方都 import 它来读配置
settings = config[os.getenv("FLASK_ENV", "development")]
