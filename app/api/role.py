"""角色管理 API"""
from flask import Blueprint, request
from app.models.role import Role
from app.extensions import db
from app.utils.response import success, error

role_bp = Blueprint('role', __name__)


@role_bp.route('/roles', methods=['GET'])
def list_roles():
    """获取所有角色（内置 + 自定义）"""
    roles = Role.get_all()
    return success([r.to_dict() for r in roles])


@role_bp.route('/roles', methods=['POST'])
def create_role():
    """创建角色（检测同名）"""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    prompt = data.get('prompt', '').strip()
    icon = data.get('icon', '🤖')

    if not name or not prompt:
        return error("角色名称和提示词不能为空", 400)
    if len(name) > 100:
        return error("角色名称不能超过100字", 400)

    # 检查同名
    existing = Role.query.filter_by(name=name).first()
    if existing:
        return error(f"角色「{name}」已存在，请使用其他名称", 409)

    role = Role.create(name=name, prompt=prompt, icon=icon)
    return success(role.to_dict(), "角色创建成功")


@role_bp.route('/roles/<role_id>', methods=['PUT'])
def update_role(role_id):
    """更新角色（允许修改所有角色，检测同名冲突）"""
    role = Role.get_by_id(role_id)
    if not role:
        return error("角色不存在", 404)

    data = request.get_json() or {}
    new_name = data.get('name', '').strip() if data.get('name') else None
    new_prompt = data.get('prompt', '').strip() if data.get('prompt') else None
    new_icon = data.get('icon')

    # 改名时检查同名（排除自身）
    if new_name:
        conflict = Role.query.filter(Role.name == new_name, Role.id != role_id).first()
        if conflict:
            return error(f"角色「{new_name}」已存在，请使用其他名称", 409)

    role.update(name=new_name, prompt=new_prompt, icon=new_icon)
    return success(role.to_dict(), "角色已更新")


@role_bp.route('/roles/<role_id>', methods=['DELETE'])
def delete_role(role_id):
    """删除角色（允许删除所有角色）"""
    role = Role.get_by_id(role_id)
    if not role:
        return error("角色不存在", 404)

    role.delete()
    return success(None, "角色已删除")
