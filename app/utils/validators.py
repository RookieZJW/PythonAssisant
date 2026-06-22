"""
数据验证工具模块
==================
提供请求数据验证相关的装饰器和工具函数，包括：
- JSON 请求体必填字段验证装饰器
- 模型名称有效性验证
- 会话 ID（UUID）格式验证

用于在视图函数执行前校验输入数据的合法性，
减少视图函数内部的校验样板代码。
"""
import re
from functools import wraps
from flask import request
from .response import error


def validate_json(*required_fields):
    """
    JSON 请求体验证装饰器
    -----------------------
    验证请求的 Content-Type 是否为 JSON，
    以及 JSON 请求体是否包含所有指定必填字段。

    用法:
        @app.route('/chat', methods=['POST'])
        @validate_json('message', 'conversation_id')
        def chat():
            data = request.get_json()
            ...

    参数:
        *required_fields: 必填字段名列表，如 'message', 'user_id' 等

    返回:
        装饰器函数，验证失败时返回标准错误响应
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # 检查请求体是否为 JSON 格式
            if not request.is_json:
                return error("请求体必须是 JSON 格式", 400)

            # 获取 JSON 数据
            data = request.get_json()
            if data is None:
                return error("请求体不能为空", 400)

            # 检查所有必填字段是否都存在
            missing = [field for field in required_fields if field not in data]
            if missing:
                return error(f"缺少必填参数: {', '.join(missing)}", 400)

            # 验证通过，执行视图函数
            return f(*args, **kwargs)
        return decorated
    return decorator


def validate_model_name(model_name):
    """
    验证模型名称是否在支持列表中
    ------------------------------
    检查传入的模型名称是否为系统支持的模型之一。

    参数:
        model_name (str): 模型名称

    返回:
        bool: True 表示模型名称有效，False 表示无效
    """
    valid_models = ["deepseek", "qwen"]
    return model_name in valid_models


def validate_conversation_id(conversation_id):
    """
    验证会话 ID 是否为有效的 UUID 格式
    ------------------------------------
    使用正则表达式校验会话 ID 是否符合 UUID v4 标准格式。

    参数:
        conversation_id (str): 会话 ID 字符串

    返回:
        bool: True 表示格式正确，False 表示格式无效
    """
    if not conversation_id:
        return False
    # UUID v4 标准正则表达式: 8-4-4-4-12 格式的十六进制字符串
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, conversation_id, re.IGNORECASE))
