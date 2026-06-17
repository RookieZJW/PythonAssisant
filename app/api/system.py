import os
from flask import Blueprint, request, send_file
from app.services.model_service import ModelService
from app.services.tool_service import ToolService
from app.config.settings import settings
from app.utils.response import success, error
from datetime import datetime

system_bp = Blueprint('system', __name__)


@system_bp.route('/health', methods=['GET'])
def health():
    """健康检查接口"""
    models = ModelService.get_available_models()
    return success({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "models": [m["name"] for m in models],
        "default_model": settings.DEFAULT_MODEL,
    })


@system_bp.route('/models', methods=['GET'])
def get_models():
    """获取可用模型列表"""
    models = ModelService.get_available_models()
    return success(models)


@system_bp.route('/tools', methods=['GET'])
def get_tools():
    """获取可用工具列表"""
    tool_names = ToolService.get_tool_names()
    return success({
        "tools": tool_names,
        "count": len(tool_names),
    })


@system_bp.route('/tools/<tool_name>', methods=['POST'])
def execute_tool(tool_name):
    """执行指定工具"""
    from flask import request
    from app.utils.response import error

    params = request.get_json() or {}
    result = ToolService.execute_tool(tool_name, **params)
    return success({"result": result})


@system_bp.route('/local-media', methods=['GET'])
def local_media():
    """代理本地文件（图片/视频），解决浏览器安全限制"""
    filepath = request.args.get('path', '')
    if not filepath or not os.path.isfile(filepath):
        return error("文件不存在: " + filepath, 404)

    # 安全检查：仅允许常见媒体格式
    ext = os.path.splitext(filepath)[1].lower()
    allowed = {'.jpg','.jpeg','.png','.gif','.webp','.bmp','.svg','.mp4','.webm','.mov','.avi'}
    if ext not in allowed:
        return error("不支持的媒体格式: " + ext, 400)

    # 判断 MIME 类型
    mime_map = {
        '.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png',
        '.gif':'image/gif','.webp':'image/webp','.bmp':'image/bmp',
        '.svg':'image/svg+xml','.mp4':'video/mp4','.webm':'video/webm',
        '.mov':'video/quicktime','.avi':'video/x-msvideo',
    }
    return send_file(filepath, mimetype=mime_map.get(ext, 'application/octet-stream'))
