from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database

db = SQLAlchemy()
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')


def init_extensions(app):
    """初始化 Flask 扩展"""
    # MySQL 自动创建数据库
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'mysql' in db_uri:
        _ensure_database_exists(db_uri)

    db.init_app(app)
    socketio.init_app(app)

    # 创建数据库表
    with app.app_context():
        db.create_all()

    # 注册 SocketIO 事件
    from .api.voice import register_socketio_events
    register_socketio_events(socketio)


def _ensure_database_exists(db_uri):
    """确保 MySQL 数据库存在，不存在则创建"""
    try:
        if not database_exists(db_uri):
            create_database(db_uri)
            print(f"[DB] 数据库已创建: {db_uri.split('@')[-1] if '@' in db_uri else db_uri}")
    except Exception as e:
        print(f"[DB] 无法自动创建数据库，请手动创建: {e}")

