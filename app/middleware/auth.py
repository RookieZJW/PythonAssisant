from functools import wraps
from flask import request, g
from app.models.user import User
from app.utils.response import error


def require_auth(optional=True):
    """API 认证中间件（装饰器）

    通过请求头 X-API-Key 进行用户认证。
    当 optional=True 时，认证失败不会阻止请求。
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            api_key = request.headers.get('X-API-Key') or request.args.get('api_key')

            if api_key:
                user = User.find_by_api_key(api_key)
                if user:
                    g.current_user = user
                elif not optional:
                    return error("无效的 API Key", 401)
            elif not optional:
                return error("请提供 API Key", 401)

            return f(*args, **kwargs)
        return decorated
    return decorator


def get_current_user():
    """获取当前认证用户"""
    return getattr(g, 'current_user', None)
