"""
Gunicorn 生产环境 Web 服务器配置文件
========================================
Gunicorn（Green Unicorn）是用于 UNIX 系统的 Python WSGI HTTP 服务器。
此配置文件用于在生产环境中以高性能模式启动应用。

启动命令:
    gunicorn -c gunicorn_config.py run:app

配置要点：
- Worker 类型选择 gevent（支持 SSE 流式响应和长连接）
- Worker 数量根据 CPU 核心数自动计算
- 内置日志配置（访问日志和错误日志分别记录）
- 支持通过环境变量 PORT 自定义端口
"""
import multiprocessing
import os

# ====== 服务器绑定 ======

# 监听地址和端口：0.0.0.0 表示监听所有网络接口
# 端口优先使用环境变量 PORT，默认 8000
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"


# ====== Worker 进程配置 ======

# Worker 进程数：CPU 核心数 * 2 + 1（官方推荐的生产配置公式）
# 例如：4 核 CPU -> 9 个 worker
workers = multiprocessing.cpu_count() * 2 + 1

# Worker 类型：使用 gevent（基于协程的异步 worker）
# 相比默认的同步 worker，gevent 能高效处理大量并发连接
# 特别适合需要 SSE 流式响应的场景
worker_class = "gevent"

# 每个 Worker 的最大并发连接数
# 仅在 gevent worker 类型下生效
worker_connections = 1000


# ====== 超时与连接配置 ======

# 请求超时时间（秒）
# 设置为 120 秒以适配 LLM 流式响应可能较长的生成时间
timeout = 120

# Keep-Alive 连接保持时间（秒）
# 在 5 秒内复用同一个 TCP 连接处理多个请求
keepalive = 5


# ====== 日志配置 ======

# 日志文件存放目录（项目根目录下的 logs/ 文件夹）
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# 访问日志文件路径
accesslog = os.path.join(log_dir, 'access.log')

# 错误日志文件路径
errorlog = os.path.join(log_dir, 'error.log')

# 日志级别：warning（仅记录警告及以上级别的日志，减少日志量）
loglevel = "warning"


# ====== 进程与守护配置 ======

# 是否以守护进程方式运行（后台运行）
# False 表示前台运行，适合 Docker 容器和 process manager 管理
daemon = False

# PID 文件路径（用于管理 Gunicorn 进程）
pidfile = os.path.join(log_dir, 'gunicorn.pid')
