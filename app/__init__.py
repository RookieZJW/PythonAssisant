"""
Python 智能助手 —— 应用初始化模块
=====================================
应用工厂（Application Factory）模式，负责创建和配置 Flask 应用实例。

主要职责：
1. 创建 Flask 应用并加载配置
2. 配置 CORS 跨域访问
3. 初始化数据库扩展（SQLAlchemy）
4. 初始化内置角色数据（幂等操作，不覆盖用户修改）
5. 注册全局错误处理器
6. 注册所有 API 蓝图（路由）
7. 设置首页路由（静态聊天界面）
"""
from flask import Flask
from flask_cors import CORS
from .extensions import db, init_extensions
from .config.settings import settings
from .utils.exceptions import register_error_handlers


def _seed_builtin_roles(app):
    """
    初始化内置角色（幂等操作）
    ----------------------------
    向数据库中写入系统预定义的角色数据。
    该操作是幂等的：如果同名内置角色已存在，则不会覆盖用户可能已做的修改。

    内置角色列表：
        - 通用助手: 基础问答能力
        - 编程老师: 循序渐进的技术教学
        - 软件工程师: 提供专业代码方案
        - 数据分析师: 数据驱动的深度洞察
        - 内容创作者: 技术文档和文章撰写
        - 翻译专家: 中英双语精准翻译

    参数:
        app: Flask 应用实例
    """
    from .models.role import Role
    builtins = [
        {"name": "通用助手", "prompt": "你是一个智能助手，请用简洁准确的语言回答用户的问题。", "icon": "🤖"},
        {"name": "编程老师", "prompt": "你是一位耐心的编程老师，擅长用通俗易懂的方式讲解技术概念。请循序渐进地引导学习者理解知识点。回答时多用比喻和实例。", "icon": "🧑‍🏫"},
        {"name": "软件工程师", "prompt": "你是一位资深软件工程师，请提供专业、可执行的代码方案。代码需包含必要的注释、错误处理和类型注解。优先考虑代码的可读性和可维护性。", "icon": "💻"},
        {"name": "数据分析师", "prompt": "你是一位数据分析专家，请基于数据提供深入的洞察分析，以结构化的方式呈现结论。优先使用列表、表格等方式组织信息。", "icon": "📊"},
        {"name": "内容创作者", "prompt": "你是一位专业的内容创作者，擅长撰写清晰流畅、逻辑严密的技术文档和文章。注重段落结构、用词精准和信息密度。", "icon": "✍️"},
        {"name": "翻译专家", "prompt": "你是一位精通中英双语的翻译专家，请准确地进行翻译，保持原文语义和风格。如果是专业内容，请保留术语的准确性。", "icon": "🌐"},
    ]
    with app.app_context():
        for b in builtins:
            # 检查同名内置角色是否已存在（防止重复插入和覆盖用户修改）
            existing = Role.query.filter_by(name=b["name"], is_builtin=True).first()
            if not existing:
                role = Role(name=b["name"], prompt=b["prompt"], icon=b["icon"], is_builtin=True)
                db.session.add(role)
        db.session.commit()


def create_app(config_name=None):
    """
    应用工厂函数
    --------------
    创建并配置 Flask 应用实例。这是整个应用的入口点，
    按顺序执行以下初始化步骤：

    1. 创建 Flask 实例，配置静态文件目录
    2. 加载设置配置
    3. 配置 CORS 跨域策略（允许 /api/* 路径的请求）
    4. 预导入所有模型以确保 SQLAlchemy 能发现它们
    5. 初始化扩展（数据库建表等）
    6. 初始化内置角色
    7. 注册全局错误处理器
    8. 注册所有 API 蓝图（url_prefix = /api/v1）
    9. 设置根路径路由，返回聊天界面首页

    参数:
        config_name (str, optional): 配置名称（当前未使用，保留扩展性）

    返回:
        配置完成的 Flask 应用实例
    """
    import os as _os
    # 1. 创建 Flask 应用实例
    # 静态文件目录指向项目根目录下的 static/ 文件夹
    app = Flask(__name__,
                static_folder=_os.path.join(_os.path.dirname(__file__), '..', 'static'),
                static_url_path='/static')

    # 2. 从 settings 对象加载 Flask 配置
    app.config.from_object(settings)

    # 3. 配置 CORS（跨域资源共享）
    if hasattr(settings, 'CORS_ORIGINS') and settings.CORS_ORIGINS:
        # 如果配置了特定的允许来源，则按路径精确配置
        CORS(app, resources={
            r"/api/*": {
                "origins": settings.CORS_ORIGINS,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-API-Key"],
                "supports_credentials": True,
                "max_age": 3600  # 预检请求缓存时间（秒）
            }
        })
    else:
        # 默认允许所有来源（开发环境适用）
        CORS(app)

    # 4. 提前导入所有模型，确保 SQLAlchemy 的 create_all 能发现它们
    from .models import User, Conversation, Message, Role, Background  # noqa

    # 5. 初始化扩展（包括数据库连接、建表等）
    init_extensions(app)

    # 6. 初始化内置角色数据
    _seed_builtin_roles(app)

    # 7. 注册全局错误处理器
    register_error_handlers(app)

    # 8. 注册所有 API 蓝图（路由）
    from .api.chat import chat_bp
    from .api.conversation import conversation_bp
    from .api.system import system_bp
    from .api.role import role_bp
    from .api.voice import voice_bp
    from .api.upload import upload_bp
    from .api.background_api import bg_bp

    # 所有蓝图统一挂载在 /api/v1 前缀下
    app.register_blueprint(chat_bp, url_prefix='/api/v1')
    app.register_blueprint(conversation_bp, url_prefix='/api/v1')
    app.register_blueprint(system_bp, url_prefix='/api/v1')
    app.register_blueprint(role_bp, url_prefix='/api/v1')
    app.register_blueprint(voice_bp, url_prefix='/api/v1')
    app.register_blueprint(upload_bp, url_prefix='/api/v1')
    app.register_blueprint(bg_bp, url_prefix='/api/v1')

    # 9. 首页路由 —— 返回聊天界面静态页面
    from flask import send_from_directory
    import os

    @app.route('/')
    def index():
        """根路径路由，返回聊天界面的 HTML 文件"""
        return send_from_directory(
            os.path.join(app.root_path, '..', 'static'),
            'index.html'
        )

    return app
