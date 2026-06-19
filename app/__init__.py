from flask import Flask
from flask_cors import CORS
from .extensions import db, init_extensions
from .config.settings import settings
from .utils.exceptions import register_error_handlers


def _seed_builtin_roles(app):
    """初始化内置角色（幂等，不覆盖用户修改）"""
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
            existing = Role.query.filter_by(name=b["name"], is_builtin=True).first()
            if not existing:
                role = Role(name=b["name"], prompt=b["prompt"], icon=b["icon"], is_builtin=True)
                db.session.add(role)
        db.session.commit()


def create_app(config_name=None):
    """应用工厂函数"""
    import os as _os
    app = Flask(__name__,
                static_folder=_os.path.join(_os.path.dirname(__file__), '..', 'static'),
                static_url_path='/static')

    # 加载配置
    app.config.from_object(settings)

    # CORS 配置
    if hasattr(settings, 'CORS_ORIGINS') and settings.CORS_ORIGINS:
        CORS(app, resources={
            r"/api/*": {
                "origins": settings.CORS_ORIGINS,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-API-Key"],
                "supports_credentials": True,
                "max_age": 3600
            }
        })
    else:
        CORS(app)

    # 提前导入所有模型，确保 create_all 能发现它们
    from .models import User, Conversation, Message, Role  # noqa

    # 初始化扩展（包括 create_all）
    init_extensions(app)

    # 初始化内置角色
    _seed_builtin_roles(app)

    # 注册错误处理
    register_error_handlers(app)

    # 注册蓝图
    from .api.chat import chat_bp
    from .api.conversation import conversation_bp
    from .api.system import system_bp
    from .api.role import role_bp
    from .api.voice import voice_bp
    from .api.upload import upload_bp

    app.register_blueprint(chat_bp, url_prefix='/api/v1')
    app.register_blueprint(conversation_bp, url_prefix='/api/v1')
    app.register_blueprint(system_bp, url_prefix='/api/v1')
    app.register_blueprint(role_bp, url_prefix='/api/v1')
    app.register_blueprint(voice_bp, url_prefix='/api/v1')
    app.register_blueprint(upload_bp, url_prefix='/api/v1')

    # 首页 - 聊天界面
    from flask import send_from_directory
    import os

    @app.route('/')
    def index():
        return send_from_directory(
            os.path.join(app.root_path, '..', 'static'),
            'index.html'
        )

    return app
