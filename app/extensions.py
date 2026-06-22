"""
Flask 扩展初始化模块
=====================
这个文件负责初始化项目用到的所有第三方扩展, 包括:
  1. SQLAlchemy (数据库 ORM, 操作 MySQL 不用写 SQL)
  2. SocketIO (WebSocket 通信, 用于语音实时对话等功能)

扩展对象在这里创建 (db 和 socketio), 然后在 app/__init__.py 的 create_app() 中
通过 init_extensions() 绑定到 Flask 应用实例上。
"""

from flask_sqlalchemy import SQLAlchemy      # Flask 的数据库扩展, 封装了 SQLAlchemy
from flask_socketio import SocketIO           # Flask 的 WebSocket 扩展
from sqlalchemy import create_engine          # SQLAlchemy 引擎 (用于检测数据库是否存在)
from sqlalchemy_utils import database_exists, create_database  # 检测/创建数据库的辅助工具

# ---- 创建扩展对象 (尚未绑定 Flask app) ----
# 数据库对象, 定义模型时用它 (db.Model), 查询时用它 (db.session)
db = SQLAlchemy()

# SocketIO 对象
#   cors_allowed_origins="*" → 允许跨域 WebSocket 连接
#   async_mode='threading'   → 使用线程模式 (兼容 Windows, 也支持 SSE)
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')


def init_extensions(app):
    """
    将扩展绑定到 Flask 应用实例上。
    这个函数在 create_app() 中被调用, 负责:
      1. 自动创建 MySQL 数据库 (如果不存在)
      2. 初始化 db 和 socketio
      3. 根据模型定义自动创建数据库表
      4. 注册 SocketIO 事件处理器
    """
    # ---- 步骤1: MySQL 自动建库 ----
    # 从配置中读取数据库连接字符串, 格式类似: mysql+pymysql://root:pass@localhost:3306/dbname
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'mysql' in db_uri:
        _ensure_database_exists(db_uri)

    # ---- 步骤2: 扩展初始化 ----
    # 把 Flask app 传给扩展, 让它们知道自己属于哪个应用
    db.init_app(app)            # SQLAlchemy 绑定到 app
    socketio.init_app(app)      # SocketIO 绑定到 app

    # ---- 步骤3: 自动建表 ----
    # db.create_all() 会扫描所有继承 db.Model 的类 (models/*.py),
    # 自动在 MySQL 中创建对应的表。表已存在则跳过。
    with app.app_context():
        db.create_all()

    # ---- 步骤4: 注册 SocketIO 事件 ----
    # 从 voice.py 导入事件注册函数, 让它能处理 /tts 相关的 WebSocket 消息
    from .api.voice import register_socketio_events
    register_socketio_events(socketio)


def _ensure_database_exists(db_uri):
    """
    检查 MySQL 数据库是否存在, 不存在则自动创建。
    例如: 如果 'smart_assistant' 库不存在, 就 CREATE DATABASE smart_assistant。

    注意: 这只创建数据库本身, 不创建表。表由 db.create_all() 创建。
    """
    try:
        if not database_exists(db_uri):
            create_database(db_uri)
            # 打印日志 (隐藏密码部分)
            safe_uri = db_uri.split('@')[-1] if '@' in db_uri else db_uri
            print(f"[DB] 数据库已创建: {safe_uri}")
    except Exception as e:
        # 权限不够或 MySQL 没启动时会到这里
        print(f"[DB] 无法自动创建数据库，请手动创建: {e}")
