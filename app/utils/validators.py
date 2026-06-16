import re
from functools import wraps
from flask import request
from .response import error


def validate_json(*required_fields):
    """验证 JSON 请求体中的必填字段

    用法:
        @app.route('/chat', methods=['POST'])
        @validate_json('message')
        def chat():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not request.is_json:
                return error("请求体必须是 JSON 格式", 400)

            data = request.get_json()
            if data is None:
                return error("请求体不能为空", 400)

            missing = [field for field in required_fields if field not in data]
            if missing:
                return error(f"缺少必填参数: {', '.join(missing)}", 400)

            return f(*args, **kwargs)
        return decorated
    return decorator


def validate_model_name(model_name):
    """验证模型名称是否有效"""
    valid_models = ["deepseek", "qwen"]
    return model_name in valid_models


def validate_conversation_id(conversation_id):
    """验证会话 ID 格式"""
    if not conversation_id:
        return False
    # UUID 格式验证
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, conversation_id, re.IGNORECASE))
