"""
系统管理模块 API 路由
========================
提供系统级别的功能接口，包括：
- 健康检查（Health Check）
- 可用模型列表查询
- 可用工具列表查询与执行
- Token 用量统计
"""
from flask import Blueprint, request
from app.services.model_service import ModelService
from app.services.tool_service import ToolService
from app.config.settings import settings
from app.utils.response import success, error
from datetime import datetime

# 创建名为 'system' 的蓝图，用于组织系统管理相关的路由
system_bp = Blueprint('system', __name__)


@system_bp.route('/health', methods=['GET'])
def health():
    """
    健康检查接口
    --------------
    返回服务的运行状态，包括当前时间戳、可用模型列表和默认模型名称。
    可用于负载均衡器的健康检查或 Docker 容器的存活探针。

    返回:
        JSON 响应，包含服务状态信息
    """
    models = ModelService.get_available_models()
    return success({
        "status": "ok",                                            # 服务状态：正常
        "timestamp": datetime.utcnow().isoformat(),                # 当前 UTC 时间戳
        "models": [m["name"] for m in models],                    # 可用模型名称列表
        "default_model": settings.DEFAULT_MODEL,                   # 系统默认模型
    })


@system_bp.route('/models', methods=['GET'])
def get_models():
    """
    获取可用模型列表
    ------------------
    返回当前系统支持的所有 AI 模型及其配置信息。

    返回:
        JSON 响应，包含模型列表（每个模型包含名称、提供商、参数等信息）
    """
    models = ModelService.get_available_models()
    return success(models)


@system_bp.route('/tools', methods=['GET'])
def get_tools():
    """
    获取可用工具列表
    ------------------
    返回当前系统注册的所有工具名称和数量。

    返回:
        JSON 响应，包含工具名称列表和总数
    """
    tool_names = ToolService.get_tool_names()
    return success({
        "tools": tool_names,           # 工具名称数组
        "count": len(tool_names),      # 工具总数
    })


@system_bp.route('/tools/<tool_name>', methods=['POST'])
def execute_tool(tool_name):
    """
    执行指定工具
    --------------
    根据工具名称调用对应的工具函数，并返回执行结果。
    工具可以是计算器、数据分析器、网络搜索等。

    路径参数:
        - tool_name: 要执行的工具名称

    请求体 JSON 字段:
        工具所需的参数，以键值对形式传入

    返回:
        JSON 响应，包含工具执行结果
    """
    from flask import request
    from app.utils.response import error

    params = request.get_json() or {}
    result = ToolService.execute_tool(tool_name, **params)
    return success({"result": result})


@system_bp.route('/stats', methods=['GET'])
def stats():
    """
    Token 用量统计接口
    --------------------
    从数据库中查询 Token 使用情况的统计数据，包括：
    - 全部历史总量（消息数、Token 数、会话数）
    - 用户输入 vs AI 输出 Token 用量
    - 今日用量统计

    返回:
        JSON 响应，包含详细的用量统计数据
    """
    from app.models.message import Message
    from app.models.conversation import Conversation
    from app.extensions import db
    from sqlalchemy import func

    # ----- 全部历史总计 -----
    # 所有消息的总 Token 消耗量
    total_tokens = db.session.query(func.coalesce(func.sum(Message.tokens), 0)).scalar()
    # 总消息条数
    total_messages = db.session.query(func.count(Message.id)).scalar() or 0
    # 总会话数
    total_convs = db.session.query(func.count(Conversation.id)).scalar() or 0

    # ----- 用户输入 vs AI 输出 -----
    # 用户（user 角色）产生的 Token 总和
    user_tokens = db.session.query(func.coalesce(func.sum(Message.tokens), 0)).filter(
        Message.role == 'user'
    ).scalar()
    # AI 助手（assistant 角色）产生的 Token 总和
    assistant_tokens = db.session.query(func.coalesce(func.sum(Message.tokens), 0)).filter(
        Message.role == 'assistant'
    ).scalar()

    # ----- 今日用量统计 -----
    today = datetime.utcnow().date()
    # 今日产生的 Token 总和
    today_tokens = db.session.query(func.coalesce(func.sum(Message.tokens), 0)).filter(
        func.date(Message.created_at) == today
    ).scalar()
    # 今日产生的消息条数
    today_messages = db.session.query(func.count(Message.id)).filter(
        func.date(Message.created_at) == today
    ).scalar() or 0

    return success({
        "total_tokens": total_tokens,                # 全部历史 Token 总量
        "total_messages": total_messages,            # 全部历史消息总量
        "total_conversations": total_convs,          # 全部历史会话总量
        "user_tokens": user_tokens,                  # 用户输入 Token 总量
        "assistant_tokens": assistant_tokens,        # AI 输出 Token 总量
        "today_tokens": today_tokens,                # 今日 Token 消耗
        "today_messages": today_messages,            # 今日消息数量
    })
