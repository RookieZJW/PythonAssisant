"""
自定义异常与全局错误处理器模块
================================
定义了一组业务相关的异常类和全局错误处理器，
用于统一处理 API 层和业务层的异常情况。

异常类层级：
    APIError (基类)
    ├── NotFoundError      (404)
    ├── BadRequestError    (400)
    ├── UnauthorizedError  (401)
    ├── RateLimitError     (429)
    └── ModelError         (503)

全局错误处理器注册函数 handle_error_handlers(app) 涵盖：
    - 自定义 APIError 及其子类
    - Flask 标准 HTTP 错误（400/404/405/500）
    - 未捕获的通用 Exception
"""
from flask import jsonify


class APIError(Exception):
    """
    自定义 API 异常基类
    ---------------------
    所有业务异常的基类，包含错误信息、HTTP 状态码和附加数据。

    属性:
        message (str): 错误描述信息
        code (int): HTTP 状态码
        data (any): 附加的错误数据（可选）
    """

    def __init__(self, message, code=500, data=None):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(message)


class NotFoundError(APIError):
    """资源未找到异常 (HTTP 404)"""
    def __init__(self, message="资源不存在"):
        super().__init__(message, code=404)


class BadRequestError(APIError):
    """请求参数错误异常 (HTTP 400)"""
    def __init__(self, message="请求参数无效"):
        super().__init__(message, code=400)


class UnauthorizedError(APIError):
    """未授权访问异常 (HTTP 401)"""
    def __init__(self, message="未授权访问"):
        super().__init__(message, code=401)


class RateLimitError(APIError):
    """请求频率限制异常 (HTTP 429)"""
    def __init__(self, message="请求过于频繁"):
        super().__init__(message, code=429)


class ModelError(APIError):
    """
    AI 模型调用异常 (HTTP 503)
    -----------------------------
    当 AI 模型服务不可用、超时或返回错误时抛出。
    使用 503 Service Unavailable 状态码表示服务暂时不可用。
    """
    def __init__(self, message="模型调用失败"):
        super().__init__(message, code=503)


def register_error_handlers(app):
    """
    注册全局错误处理器
    --------------------
    为 Flask 应用注册各类错误处理函数，确保所有异常都返回统一的 JSON 格式。
    包含对自定义异常类和标准 HTTP 错误的处理。

    参数:
        app: Flask 应用实例
    """
    # ----- 自定义异常处理器 -----

    @app.errorhandler(APIError)
    def handle_api_error(e):
        """
        处理所有 APIError 及其子类异常
        ---------------------------------
        记录错误日志并以统一 JSON 格式返回。
        """
        app.logger.error(f"APIError: {e.message}", exc_info=True)
        return jsonify({
            "code": e.code,
            "message": e.message,
            "data": e.data,
        }), e.code

    # ----- Flask 标准 HTTP 错误处理器 -----

    @app.errorhandler(400)
    def handle_400(e):
        """处理 400 Bad Request"""
        return jsonify({
            "code": 400,
            "message": "请求参数无效",
            "data": None,
        }), 400

    @app.errorhandler(404)
    def handle_404(e):
        """处理 404 Not Found"""
        return jsonify({
            "code": 404,
            "message": "请求的资源不存在",
            "data": None,
        }), 404

    @app.errorhandler(405)
    def handle_405(e):
        """处理 405 Method Not Allowed"""
        return jsonify({
            "code": 405,
            "message": "请求方法不允许",
            "data": None,
        }), 405

    @app.errorhandler(500)
    def handle_500(e):
        """处理 500 Internal Server Error"""
        app.logger.error(f"Internal Server Error: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": "服务器内部错误",
            "data": None,
        }), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        """
        捕获所有未处理的异常（兜底处理器）
        ------------------------------------
        防止未捕获异常导致服务器崩溃，确保始终返回 JSON 格式的错误响应。
        """
        app.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": "服务器内部错误",
            "data": None,
        }), 500
