"""
应用启动入口
"""
import os
from app import create_app
from app.extensions import socketio

# 根据环境变量创建应用实例
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # 开发环境启动
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'

    # 使用 SocketIO 启动（兼容 WebSocket + HTTP）
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
