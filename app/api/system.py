from flask import Blueprint
from app.services.model_service import ModelService
from app.services.tool_service import ToolService
from app.config.settings import settings
from app.utils.response import success
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
