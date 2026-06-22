"""
日志记录中间件模块
====================
提供应用日志系统的配置和请求日志记录功能。

主要功能：
- 初始化应用日志系统（文件日志 + 控制台日志）
- 按日期生成日志文件（每日滚动）
- 请求/响应日志记录（方法、路径、状态码、耗时）
- 开发模式输出 DEBUG 级别日志，生产模式输出 WARNING 级别日志
"""
import logging
import os
from datetime import datetime
from flask import request, g
from functools import wraps


def setup_logging(app):
    """
    配置应用日志系统
    ------------------
    设置两种日志输出方式：
    1. 文件日志：按日期分文件保存到 logs/ 目录
    2. 控制台日志：实时输出到终端

    日志级别：
    - 调试模式（app.debug=True）：DEBUG 级别
    - 生产模式（app.debug=False）：WARNING 级别

    参数:
        app: Flask 应用实例

    返回:
        配置完成后的 Flask 应用实例
    """
    # 创建日志目录（位于项目根目录的 logs/ 文件夹）
    log_dir = os.path.join(app.root_path, '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # 根据调试模式设置日志级别
    log_level = logging.DEBUG if app.debug else logging.WARNING

    # ---- 文件处理器 ----
    # 按当前日期生成日志文件名，实现每日日志滚动
    log_file = os.path.join(log_dir, f'app_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    # ---- 控制台处理器 ----
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '[%(levelname)s] %(message)s'
    ))

    # 将处理器添加到 Flask 应用的日志器中
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)

    return app


def request_logger(f):
    """
    请求日志记录装饰器
    --------------------
    自动记录每个 HTTP 请求和对应的响应信息，包括：
    - 请求方法、路径、客户端 IP
    - 响应状态码、处理耗时（毫秒）

    用法:
        @app.route('/api/chat')
        @request_logger
        def chat():
            ...

    参数:
        f: 被装饰的视图函数

    返回:
        装饰后的函数
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import current_app
        start_time = datetime.now()

        # 记录请求信息：HTTP 方法、请求路径、客户端 IP 地址
        current_app.logger.info(
            f"[请求] {request.method} {request.path} "
            f"from {request.remote_addr}"
        )

        # 执行被装饰的视图函数，获取响应
        response = f(*args, **kwargs)

        # 记录响应信息：状态码、处理耗时（单位毫秒）
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        status_code = getattr(response, 'status_code', 200)
        current_app.logger.info(
            f"[响应] {request.method} {request.path} "
            f"-> {status_code} ({elapsed:.0f}ms)"
        )

        return response
    return decorated
