"""角色管理 API"""
from flask import Blueprint, request
from app.models.role import Role
from app.utils.response import success, error

role_bp = Blueprint('role', __name__)


@role_bp.route('/roles', methods=['GET'])
def list_roles():
    """获取所有角色（内置 + 自定义）"""
    roles = Role.get_all()
    return success([r.to_dict() for r in roles])


@role_bp.route('/roles', methods=['POST'])
def create_role():
    """创建自定义角色"""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    prompt = data.get('prompt', '').strip()
    icon = data.get('icon', '🤖')

    if not name or not prompt:
        return error("角色名称和提示词不能为空", 400)
    if len(name) > 100:
        return error("角色名称不能超过100字", 400)

    role = Role.create(name=name, prompt=prompt, icon=icon)
    return success(role.to_dict(), "角色创建成功")


@role_bp.route('/roles/<role_id>', methods=['PUT'])
def update_role(role_id):
    """更新自定义角色"""
    role = Role.get_by_id(role_id)
    if not role:
        return error("角色不存在", 404)
    if role.is_builtin:
        return error("内置角色不可修改", 403)

    data = request.get_json() or {}
    role.update(
        name=data.get('name'),
        prompt=data.get('prompt'),
        icon=data.get('icon'),
    )
    return success(role.to_dict(), "角色已更新")


@role_bp.route('/roles/<role_id>', methods=['DELETE'])
def delete_role(role_id):
    """删除自定义角色"""
    role = Role.get_by_id(role_id)
    if not role:
        return error("角色不存在", 404)
    if role.is_builtin:
        return error("内置角色不可删除", 403)

    role.delete()
    return success(None, "角色已删除")
