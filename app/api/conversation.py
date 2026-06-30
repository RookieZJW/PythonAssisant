"""
会话管理模块 API 路由
=========================
提供会话（Conversation）的 CRUD 操作接口，包括：
- 创建新会话
- 获取会话列表
- 获取会话详情（含消息记录）
- 修改会话标题
- 删除会话
- 获取会话消息列表
- 导出会话为 Markdown / 文本文件
"""
from flask import Blueprint, request, Response, session
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.role import Role
from app.utils.response import success, error
from app.extensions import db
from datetime import datetime

# 创建名为 'conversation' 的蓝图，用于组织会话相关的路由
conversation_bp = Blueprint('conversation', __name__)


@conversation_bp.route('/conversations', methods=['POST'])
def create_conversation():
    """
    创建新会话
    ------------
    接收前端传入的标题、模型、用户 ID 等参数，在数据库中创建一条新会话记录。

    请求体 JSON 字段:
        - title (可选): 会话标题，默认 "新对话"
        - model (可选): 使用的模型名称，默认 "deepseek"
        - user_id (可选): 用户标识，默认 "anonymous"
        - role_id (可选): 绑定角色 ID

    返回:
        JSON 响应，包含新创建的会话信息
    """
    data = request.get_json() or {}
    title = data.get('title', '新对话')
    model = data.get('model', 'deepseek')
    user_id = session.get('user_id', data.get('user_id', 'anonymous'))
    role_id = data.get('role_id', None)

    conversation = Conversation.create(title=title, model=model, user_id=user_id, role_id=role_id)
    return success(conversation.to_dict(), "会话创建成功")


@conversation_bp.route('/conversations', methods=['GET'])
def list_conversations():
    """
    获取会话列表
    --------------
    支持分页查询，返回指定用户的会话列表，按更新时间倒序排列。

    查询参数:
        - page (可选): 页码，默认 1
        - page_size (可选): 每页条数，默认 20
        - user_id (可选): 用户标识，默认 "anonymous"

    返回:
        JSON 响应，包含分页后的会话列表数据
    """
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    from flask import session; uid = session.get('user_id','')

    result = Conversation.get_list(user_id=uid or 'anonymous', page=page, page_size=page_size)
    return success(result)


@conversation_bp.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """
    获取会话详情（含消息列表）
    ----------------------------
    根据会话 ID 查询会话信息，并加载该会话下最近 50 条消息记录一并返回。

    路径参数:
        - conversation_id: 会话的唯一标识符（UUID 格式）

    返回:
        JSON 响应，包含会话元数据和消息列表
    """
    conversation = Conversation.query.filter_by(
        id=conversation_id,
            ).first()

    if not conversation:
        return error("会话不存在", 404)

    messages = Message.get_history(conversation_id, limit=50)
    data = conversation.to_dict()
    data['messages'] = messages
    return success(data)


@conversation_bp.route('/conversations/<conversation_id>', methods=['PUT'])
def update_conversation(conversation_id):
    """
    修改会话标题
    --------------
    更新指定会话的标题，要求标题非空且长度不超过 200 字。

    路径参数:
        - conversation_id: 会话的唯一标识符

    请求体 JSON 字段:
        - title (必填): 新的会话标题

    返回:
        JSON 响应，包含更新后的会话信息
    """
    conversation = Conversation.query.filter_by(id=conversation_id).first()
    if not conversation:
        return error("会话不存在", 404)
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    if not title or len(title) > 200:
        return error("标题不能为空且不超过200字", 400)
    conversation.title = title
    db.session.commit()
    return success(conversation.to_dict(), "标题已更新")


@conversation_bp.route('/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """
    删除会话（含所有关联消息）
    --------------------------
    从数据库中彻底删除指定会话及其关联的所有消息记录。

    路径参数:
        - conversation_id: 会话的唯一标识符

    返回:
        JSON 响应，表示删除成功
    """
    conversation = Conversation.query.filter_by(id=conversation_id).first()
    if not conversation:
        return error("会话不存在", 404)
    conversation.hard_delete()
    return success(None, "会话及消息已删除")


@conversation_bp.route('/conversations/<conversation_id>/messages', methods=['GET'])
def get_messages(conversation_id):
    """
    获取会话消息列表
    ------------------
    根据会话 ID 查询该会话下的消息记录，支持限制返回条数。

    路径参数:
        - conversation_id: 会话的唯一标识符

    查询参数:
        - limit (可选): 返回消息的最大条数，默认 20

    返回:
        JSON 响应，包含消息列表
    """
    conversation = Conversation.query.filter_by(
        id=conversation_id,
            ).first()

    if not conversation:
        return error("会话不存在", 404)

    limit = request.args.get('limit', 20, type=int)
    messages = Message.get_history(conversation_id, limit=limit)
    return success(messages)


@conversation_bp.route('/conversations/<conversation_id>/export', methods=['GET'])
def export_conversation(conversation_id):
    """
    导出对话为 Markdown / 文本文件
    --------------------------------
    将会话标题、角色名称、模型信息和所有消息记录导出为可下载的文件。
    支持导出为 Markdown 格式（默认）和纯文本格式。
    同时会进行文件名安全处理，移除特殊字符。

    路径参数:
        - conversation_id: 会话的唯一标识符

    查询参数:
        - format (可选): 导出格式，'markdown'（默认）或 'txt'

    返回:
        文件流响应（Content-Disposition 附件下载）
    """
    conversation = Conversation.query.filter_by(
        id=conversation_id,     ).first()
    if not conversation:
        return error("会话不存在", 404)

    messages = Message.get_history(conversation_id, limit=9999)
    fmt = request.args.get('format', 'markdown')

    # 获取绑定的角色名称，若未绑定角色则显示"默认助手"
    role_name = "默认助手"
    if conversation.role_id:
        role = Role.query.get(conversation.role_id)
        if role:
            role_name = role.name

    if fmt == 'txt':
        # ----- 纯文本格式导出 -----
        lines = []
        lines.append(f"标题: {conversation.title}")
        lines.append(f"角色: {role_name}")
        lines.append(f"模型: {conversation.model}")
        lines.append(f"时间: {conversation.created_at.strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 50)
        for m in messages:
            prefix = "🧑 用户" if m['role'] == 'user' else "🤖 助手"
            lines.append(f"\n{prefix}:\n{m['content']}")
        content = "\n".join(lines)
        filename = f"{conversation.title}.txt"
        mime = "text/plain; charset=utf-8"
    else:
        # ----- Markdown 格式导出（默认） -----
        lines = []
        lines.append(f"# {conversation.title}")
        lines.append("")
        lines.append(f"> 角色: {role_name} | 模型: {conversation.model} | {conversation.created_at.strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        lines.append("---")
        for m in messages:
            if m['role'] == 'user':
                lines.append(f"\n### 🧑 用户\n\n{m['content']}\n")
            else:
                lines.append(f"\n### 🤖 {role_name}\n\n{m['content']}\n")
        content = "\n".join(lines)
        filename = f"{conversation.title}.md"
        mime = "text/markdown; charset=utf-8"

    # 文件名安全处理：只保留字母、数字、空格、连字符和下划线
    safe_name = "".join(c for c in conversation.title if c.isalnum() or c in (' ', '-', '_')).strip() or "对话"
    filename = f"{safe_name}.{'md' if fmt != 'txt' else 'txt'}"

    # 返回文件下载响应，使用 UTF-8 编码的文件名以支持中文
    return Response(
        content.encode('utf-8'),
        mimetype=mime,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        }
    )
