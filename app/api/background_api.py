"""自定义背景历史 API"""
from flask import Blueprint, request
from app.models.background import Background
from app.utils.response import success, error

bg_bp = Blueprint('background_api', __name__)


@bg_bp.route('/backgrounds', methods=['GET'])
def list_backgrounds():
    """获取背景历史列表"""
    items = Background.get_all()
    return success([b.to_dict() for b in items])


@bg_bp.route('/backgrounds', methods=['POST'])
def save_background():
    """保存背景到历史"""
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url: return error("URL 不能为空", 400)

    bg = Background.add(
        url=url,
        bg_type=data.get('type', 'image'),
        mode=data.get('mode', 'full'),
        size=data.get('size', 'cover'),
    )
    return success(bg.to_dict(), "已保存")


@bg_bp.route('/backgrounds/<bg_id>', methods=['DELETE'])
def delete_background(bg_id):
    """删除背景记录"""
    Background.delete_by_id(bg_id)
    return success(None, "已删除")
