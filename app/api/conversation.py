from flask import Blueprint, request, Response
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.role import Role
from app.utils.response import success, error
from app.extensions import db
from datetime import datetime

conversation_bp = Blueprint('conversation', __name__)


@conversation_bp.route('/conversations', methods=['POST'])
def create_conversation():
    """创建新会话"""
    data = request.get_json() or {}
    title = data.get('title', '新对话')
    model = data.get('model', 'deepseek')
    user_id = data.get('user_id', 'anonymous')
    role_id = data.get('role_id', None)

    conversation = Conversation.create(title=title, model=model, user_id=user_id, role_id=role_id)
    return success(conversation.to_dict(), "会话创建成功")


@conversation_bp.route('/conversations', methods=['GET'])
def list_conversations():
    """获取会话列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    user_id = request.args.get('user_id', 'anonymous')

    result = Conversation.get_list(user_id=user_id, page=page, page_size=page_size)
    return success(result)


@conversation_bp.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """获取会话详情（含消息列表）"""
    conversation = Conversation.query.filter_by(
        id=conversation_id,
            ).first()

    if not conversation:
        return error("会话不存在", 404)

    messages = Message.get_history(conversation_id, limit=50)
    data = conversation.to_dict()
    data['messages'] = messages
    return success(data)


@conversation_bp.route('/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """删除会话（软删除）"""
    conversation = Conversation.query.filter_by(
        id=conversation_id,
            ).first()

    if not conversation:
        return error("会话不存在", 404)

    conversation.hard_delete()
    return success(None, "会话及消息已删除")


@conversation_bp.route('/conversations/<conversation_id>/messages', methods=['GET'])
def get_messages(conversation_id):
    """获取会话消息列表"""
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
    """导出对话为 Markdown 文件"""
    conversation = Conversation.query.filter_by(
        id=conversation_id,     ).first()
    if not conversation:
        return error("会话不存在", 404)

    messages = Message.get_history(conversation_id, limit=9999)
    fmt = request.args.get('format', 'markdown')

    # 获取角色信息
    role_name = "默认助手"
    if conversation.role_id:
        role = Role.query.get(conversation.role_id)
        if role: role_name = role.name

    if fmt == 'txt':
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

    # 文件名安全处理
    safe_name = "".join(c for c in conversation.title if c.isalnum() or c in (' ', '-', '_')).strip() or "对话"
    filename = f"{safe_name}.{'md' if fmt != 'txt' else 'txt'}"

    return Response(
        content.encode('utf-8'),
        mimetype=mime,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        }
    )
