"""
角色管理模块 API 路由
========================
提供角色（Role）的 CRUD 操作接口，包括：
- 获取所有角色列表（内置角色 + 用户自定义角色）
- 创建新角色（检测名称冲突）
- 更新角色信息（检测名称冲突，排除自身）
- 删除角色
"""
from flask import Blueprint, request
from app.models.role import Role
from app.extensions import db
from app.utils.response import success, error

# 创建名为 'role' 的蓝图，用于组织角色管理相关的路由
role_bp = Blueprint('role', __name__)


@role_bp.route('/roles', methods=['GET'])
def list_roles():
    """
    获取所有角色（内置 + 自定义）
    -------------------------------
    返回系统中全部可用角色列表，包含系统内置角色和用户创建的自定义角色。

    返回:
        JSON 响应，包含角色对象列表（每个角色包含 id、name、prompt、icon 等字段）
    """
    roles = Role.get_all()
    return success([r.to_dict() for r in roles])


@role_bp.route('/roles', methods=['POST'])
def create_role():
    """
    创建新角色（检测同名冲突）
    ----------------------------
    接收角色名称、提示词和图标参数，在数据库中创建一条新角色记录。
    创建前会检查角色名称是否已存在，避免重复。

    请求体 JSON 字段:
        - name (必填): 角色名称，不超过 100 字
        - prompt (必填): 角色提示词（system prompt）
        - icon (可选): 角色图标 emoji，默认 "🤖"

    返回:
        JSON 响应，包含新创建的角色信息
    """
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    prompt = data.get('prompt', '').strip()
    icon = data.get('icon', '🤖')

    # 校验必填字段
    if not name or not prompt:
        return error("角色名称和提示词不能为空", 400)
    if len(name) > 100:
        return error("角色名称不能超过100字", 400)

    # 检查同名角色是否已存在
    existing = Role.query.filter_by(name=name).first()
    if existing:
        return error(f"角色「{name}」已存在，请使用其他名称", 409)

    role = Role.create(name=name, prompt=prompt, icon=icon)
    return success(role.to_dict(), "角色创建成功")


@role_bp.route('/roles/<role_id>', methods=['PUT'])
def update_role(role_id):
    """
    更新角色信息（允许修改所有角色，检测同名冲突）
    ------------------------------------------------
    根据角色 ID 更新角色的名称、提示词和/或图标。
    若修改名称会检测同名冲突（排除当前角色自身），避免重名。

    路径参数:
        - role_id: 角色的唯一标识符

    请求体 JSON 字段（至少提供一个）:
        - name (可选): 新的角色名称
        - prompt (可选): 新的角色提示词
        - icon (可选): 新的角色图标

    返回:
        JSON 响应，包含更新后的角色信息
    """
    role = Role.get_by_id(role_id)
    if not role:
        return error("角色不存在", 404)

    data = request.get_json() or {}
    new_name = data.get('name', '').strip() if data.get('name') else None
    new_prompt = data.get('prompt', '').strip() if data.get('prompt') else None
    new_icon = data.get('icon')

    # 改名时检查除自身外是否已有同名角色
    if new_name:
        conflict = Role.query.filter(Role.name == new_name, Role.id != role_id).first()
        if conflict:
            return error(f"角色「{new_name}」已存在，请使用其他名称", 409)

    role.update(name=new_name, prompt=new_prompt, icon=new_icon)
    return success(role.to_dict(), "角色已更新")


@role_bp.route('/roles/<role_id>', methods=['DELETE'])
def delete_role(role_id):
    """
    删除角色（允许删除所有角色，含内置角色）
    ------------------------------------------
    根据角色 ID 从数据库中删除指定的角色记录。

    路径参数:
        - role_id: 要删除的角色的唯一标识符

    返回:
        JSON 响应，表示删除成功
    """
    role = Role.get_by_id(role_id)
    if not role:
        return error("角色不存在", 404)

    role.delete()
    return success(None, "角色已删除")
