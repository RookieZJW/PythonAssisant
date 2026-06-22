"""
应用启动入口
============
这是整个项目的启动文件, 用 `python run.py` 命令运行。
主要做两件事:
  1. 根据环境变量创建 Flask 应用实例
  2. 启动 SocketIO 服务器 (支持 WebSocket + 普通 HTTP)
"""

import os
from app import create_app                 # 导入应用工厂函数 (在 app/__init__.py 中定义)
from app.extensions import socketio        # 导入 SocketIO 实例 (用于语音对话等实时功能)

# 根据 FLASK_ENV 环境变量创建应用实例
#   development → 开发模式 (DEBUG=True, SQLite/本地MySQL)
#   production  → 生产模式 (DEBUG=False)
#   testing     → 测试模式 (SQLite 内存数据库)
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # ---- 开发环境启动 ----
    host = os.getenv('HOST', '0.0.0.0')              # 监听地址, 0.0.0.0 表示局域网也可访问
    port = int(os.getenv('PORT', 5000))               # 监听端口

    # 关闭 debug 自动重载 (Windows 下 Flask 的 auto-reloader 容易缓存旧代码不更新)
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    # 用 SocketIO 启动 (替代 app.run())
    #   allow_unsafe_werkzeug=True 是 Flask-SocketIO 在最新版需要的一个兼容参数
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
