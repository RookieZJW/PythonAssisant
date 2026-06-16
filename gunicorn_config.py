"""
Gunicorn 生产环境配置
启动命令: gunicorn -c gunicorn_config.py run:app
"""
import multiprocessing
import os

# 绑定地址
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Worker 进程数
workers = multiprocessing.cpu_count() * 2 + 1

# Worker 类型 (gevent 支持 SSE 流式响应)
worker_class = "gevent"

# 每个 Worker 最大并发连接数
worker_connections = 1000

# 请求超时时间（秒）
timeout = 120

# Keep-Alive 时间
keepalive = 5

# 日志配置
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

accesslog = os.path.join(log_dir, 'access.log')
errorlog = os.path.join(log_dir, 'error.log')
loglevel = "warning"

# 是否守护进程化
daemon = False

# PID 文件
pidfile = os.path.join(log_dir, 'gunicorn.pid')
