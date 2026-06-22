"""
API 认证中间件模块
======================
提供基于 API Key 的用户认证功能。
通过 Flask 的请求头 X-API-Key 或 URL 查询参数 api_key 进行身份验证。

支持两种模式：
- 可选认证（默认）：认证失败不阻止请求，g.current_user 可能为 None
- 强制认证：认证失败时返回 401 错误
"""
from functools import wraps
from flask import request, g
from app.models.user import User
from app.utils.response import error


def require_auth(optional=True):
    """
    API 认证中间件装饰器
    -----------------------
    通过检查请求头 X-API-Key 或查询参数 api_key 来验证用户身份。
    验证成功后，将用户对象注入到 Flask 全局对象 g.current_user 中。

    参数:
        optional (bool): 是否可选认证。
            - True（默认）: 认证失败不会阻止请求，仅 g.current_user 为 None
            - False: 认证失败返回 401 错误响应

    用法:
        @app.route('/api/protected')
        @require_auth(optional=False)
        def protected_route():
            user = get_current_user()
            ...

    返回:
        装饰器函数
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # 从请求头或 URL 查询参数中获取 API Key
            api_key = request.headers.get('X-API-Key') or request.args.get('api_key')

            if api_key:
                # 根据 API Key 查找对应用户
                user = User.find_by_api_key(api_key)
                if user:
                    # 认证成功，将用户对象注入全局上下文
                    g.current_user = user
                elif not optional:
                    # 强制认证模式下，API Key 无效则返回 401
                    return error("无效的 API Key", 401)
            elif not optional:
                # 强制认证模式下，未提供 API Key 则返回 401
                return error("请提供 API Key", 401)

            # 执行被装饰的视图函数
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_current_user():
    """
    获取当前认证用户
    ------------------
    从 Flask 全局上下文 g 中获取已认证的用户对象。
    若未认证（可选模式且未提供有效 API Key），返回 None。

    返回:
        User 对象 或 None（未认证时）
    """
    return getattr(g, 'current_user', None)
