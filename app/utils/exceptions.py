from flask import jsonify


class APIError(Exception):
    """自定义 API 异常"""

    def __init__(self, message, code=500, data=None):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(message)


class NotFoundError(APIError):
    """资源未找到异常"""
    def __init__(self, message="资源不存在"):
        super().__init__(message, code=404)


class BadRequestError(APIError):
    """请求参数错误"""
    def __init__(self, message="请求参数无效"):
        super().__init__(message, code=400)


class UnauthorizedError(APIError):
    """未授权异常"""
    def __init__(self, message="未授权访问"):
        super().__init__(message, code=401)


class RateLimitError(APIError):
    """限流异常"""
    def __init__(self, message="请求过于频繁"):
        super().__init__(message, code=429)


class ModelError(APIError):
    """模型调用异常"""
    def __init__(self, message="模型调用失败"):
        super().__init__(message, code=503)


def register_error_handlers(app):
    """注册全局错误处理器"""

    @app.errorhandler(APIError)
    def handle_api_error(e):
        app.logger.error(f"APIError: {e.message}", exc_info=True)
        return jsonify({
            "code": e.code,
            "message": e.message,
            "data": e.data,
        }), e.code

    @app.errorhandler(400)
    def handle_400(e):
        return jsonify({
            "code": 400,
            "message": "请求参数无效",
            "data": None,
        }), 400

    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({
            "code": 404,
            "message": "请求的资源不存在",
            "data": None,
        }), 404

    @app.errorhandler(405)
    def handle_405(e):
        return jsonify({
            "code": 405,
            "message": "请求方法不允许",
            "data": None,
        }), 405

    @app.errorhandler(500)
    def handle_500(e):
        app.logger.error(f"Internal Server Error: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": "服务器内部错误",
            "data": None,
        }), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": "服务器内部错误",
            "data": None,
        }), 500
