from flask import jsonify


def success(data=None, message="success", code=200):
    """统一成功响应"""
    return jsonify({
        "code": code,
        "message": message,
        "data": data,
    }), code


def error(message="服务器内部错误", code=500, data=None):
    """统一错误响应"""
    return jsonify({
        "code": code,
        "message": message,
        "data": data,
    }), code


def paginated(items, total, page, page_size):
    """分页响应"""
    return success({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    })
