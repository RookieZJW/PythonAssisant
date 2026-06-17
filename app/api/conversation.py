from flask import Blueprint, request
from app.models.conversation import Conversation
from app.models.message import Message
from app.utils.response import success, error
from app.extensions import db

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
        is_deleted=False
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
        is_deleted=False
    ).first()

    if not conversation:
        return error("会话不存在", 404)

    conversation.soft_delete()
    return success(None, "会话已删除")


@conversation_bp.route('/conversations/<conversation_id>/messages', methods=['GET'])
def get_messages(conversation_id):
    """获取会话消息列表"""
    conversation = Conversation.query.filter_by(
        id=conversation_id,
        is_deleted=False
    ).first()

    if not conversation:
        return error("会话不存在", 404)

    limit = request.args.get('limit', 20, type=int)
    messages = Message.get_history(conversation_id, limit=limit)
    return success(messages)
