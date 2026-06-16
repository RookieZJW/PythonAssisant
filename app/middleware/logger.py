import logging
import os
from datetime import datetime
from flask import request, g
from functools import wraps


def setup_logging(app):
    """配置应用日志系统"""
    log_dir = os.path.join(app.root_path, '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # 设置日志级别
    log_level = logging.DEBUG if app.debug else logging.WARNING

    # 文件处理器
    log_file = os.path.join(log_dir, f'app_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '[%(levelname)s] %(message)s'
    ))

    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)

    return app


def request_logger(f):
    """请求日志装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import current_app
        start_time = datetime.now()

        # 记录请求
        current_app.logger.info(
            f"[请求] {request.method} {request.path} "
            f"from {request.remote_addr}"
        )

        response = f(*args, **kwargs)

        # 记录响应
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        status_code = getattr(response, 'status_code', 200)
        current_app.logger.info(
            f"[响应] {request.method} {request.path} "
            f"-> {status_code} ({elapsed:.0f}ms)"
        )

        return response
    return decorated
