"""
统一响应格式工具模块
======================
提供标准化的 API 响应格式，确保所有接口返回一致的 JSON 结构。

响应格式：
    {
        "code": 200,      # HTTP 状态码 / 业务状态码
        "message": "...", # 提示信息
        "data": ...       # 响应数据（可为任意类型或 null）
    }

函数：
    - success(data, message, code):  成功响应
    - error(message, code, data):    错误响应
    - paginated(items, total, page, page_size): 分页响应
"""
from flask import jsonify


def success(data=None, message="success", code=200):
    """
    统一成功响应
    --------------
    生成标准格式的成功 JSON 响应。

    参数:
        data: 响应数据，可为任意 JSON 可序列化类型（dict、list、str 等），默认 None
        message: 成功提示信息，默认 "success"
        code: HTTP 状态码，默认 200

    返回:
        Flask Response 对象（JSON 格式）
    """
    return jsonify({
        "code": code,
        "message": message,
        "data": data,
    }), code


def error(message="服务器内部错误", code=500, data=None):
    """
    统一错误响应
    --------------
    生成标准格式的错误 JSON 响应。

    参数:
        message: 错误描述信息，默认 "服务器内部错误"
        code: HTTP 状态码，默认 500
        data: 附加错误数据（可选），默认 None

    返回:
        Flask Response 对象（JSON 格式）
    """
    return jsonify({
        "code": code,
        "message": message,
        "data": data,
    }), code


def paginated(items, total, page, page_size):
    """
    分页响应
    ----------
    生成标准格式的分页数据响应。
    包含列表数据、总数、当前页码和每页条数。

    参数:
        items: 当前页的数据列表
        total: 数据总条数
        page: 当前页码（从 1 开始）
        page_size: 每页的数据条数

    返回:
        Flask Response 对象（JSON 格式），包含分页元数据
    """
    return success({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    })
