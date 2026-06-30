# -*- coding: utf-8 -*-
"""
自定义角色（Role）模型模块

本模块定义了 Role 数据库模型，用于存储和管理用户自定义的 AI 角色。
每个角色包含名称、系统提示词（prompt）、图标等属性。
角色可以用于对话，当用户在对话中选择了某个角色后，该角色的系统提示词
将被注入到对话上下文中，从而影响 AI 的回复风格和行为。

支持两种角色类型：
  - 内置角色（is_builtin=True）：系统预置的默认角色，不可被用户删除
  - 自定义角色（is_builtin=False）：用户自行创建的角色，支持编辑和删除
"""

# 自定义角色模型
from app.extensions import db          # 导入 Flask-SQLAlchemy 数据库扩展实例
from datetime import datetime           # 导入 datetime 用于处理时间戳
import uuid                             # 导入 uuid 用于生成唯一标识符


class Role(db.Model):
    """
    自定义角色模型类

    对应数据库中的 'roles' 表，用于存储 AI 助手的角色设定信息。
    每个角色有一套独立的系统提示词（prompt），当在会话中选择该角色后，
    对应的系统提示词将被用于指导 AI 的回复风格和行为模式。

    属性:
        id: 角色唯一标识符（UUID 字符串，主键）
        name: 角色名称
        prompt: 角色的系统提示词（System Prompt），用于定义行为风格
        icon: 角色图标（Emoji 字符串），默认表情为 '🤖'
        is_builtin: 是否为系统内置角色（内置角色不可删除）
        created_at: 角色创建时间戳
        updated_at: 角色最后更新时间戳（自动更新）
    """
    __tablename__ = 'roles'
    # 表级配置：指定 MySQL 字符集为 utf8mb4，支持存储 Emoji 等四字节 Unicode 字符
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    # ---- 数据库字段定义 ----
    # 角色 ID：使用 UUID 生成 36 位字符串作为主键
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 角色名称：最大长度 100 字符，不允许为空
    name = db.Column(db.String(100), nullable=False)
    # 系统提示词：使用 Text 类型存储较长文本，定义角色的行为风格和知识背景
    prompt = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.String(64), nullable=True, default=None)
    # 角色图标：最大长度 10 字符（通常使用单个 Emoji），默认值为 '🤖'
    icon = db.Column(db.String(10), default='🤖')
    # 是否为内置角色：布尔值，True 表示系统预置，不可删除；False 表示用户自定义
    is_builtin = db.Column(db.Boolean, default=False)
    # 创建时间：默认值为当前 UTC 时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # 更新时间：创建时默认为当前时间，每次更新记录时自动刷新为当前时间
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def create(cls, name, prompt, icon='🤖', user_id=None):
        """
        创建新的自定义角色

        这是一个类方法，用于创建并持久化一个新的自定义角色到数据库中。
        新创建的角色默认 is_builtin 为 False（非内置角色）。

        参数:
            name (str): 角色名称
            prompt (str): 角色的系统提示词（System Prompt）
            icon (str): 角色图标（Emoji），默认为 '🤖'

        返回:
            Role: 新创建并已持久化的角色实例
        """
        # 构造 Role 实例，默认 is_builtin=False（用户自定义角色）
        role = cls(name=name, prompt=prompt, icon=icon, is_builtin=False, user_id=user_id)
        # 添加到数据库会话并提交事务
        db.session.add(role)
        db.session.commit()
        return role

    @classmethod
    def get_all(cls, user_id=None):
        """
        获取所有角色列表

        这是一个类方法，用于查询数据库中所有角色的完整列表。
        排序规则：内置角色优先显示（is_builtin 降序），同优先级内按创建时间升序排列。

        返回:
            list: Role 实例列表，按"内置角色优先、按创建时间升序"排列
        """
        # 按 is_builtin 降序（内置角色在前），然后按创建时间升序排列
        return cls.query.filter((cls.is_builtin == True) | (cls.user_id == user_id) if user_id else cls.is_builtin == True).order_by(cls.is_builtin.desc(), cls.created_at.asc()).all()

    @classmethod
    def get_by_id(cls, role_id):
        """
        根据角色 ID 获取单个角色

        这是一个类方法，通过主键查询指定的角色记录。

        参数:
            role_id (str): 角色 ID（UUID 字符串）

        返回:
            Role or None: 找到的角色实例，若不存在则返回 None
        """
        return cls.query.get(role_id)

    def update(self, name=None, prompt=None, icon=None):
        """
        更新角色信息

        实例方法，用于更新当前角色的名称、提示词和图标属性。
        仅更新显式提供的参数，未提供的属性保持不变。
        更新后自动提交到数据库。

        参数:
            name (str, optional): 新的角色名称，若为 None 则不更新
            prompt (str, optional): 新的系统提示词，若为 None 则不更新
            icon (str, optional): 新的角色图标，若为 None 则不更新

        返回:
            Role: 更新后的角色实例自身（支持链式调用）
        """
        # 仅当参数不为 None 时更新对应字段
        if name: self.name = name
        if prompt: self.prompt = prompt
        if icon: self.icon = icon
        # 提交变更到数据库
        db.session.commit()
        return self

    def delete(self):
        """
        删除当前角色

        实例方法，从数据库中永久删除当前角色记录。
        注意：此方法不会检查 is_builtin 属性，调用前应由业务逻辑层
        确保内置角色不会被意外删除。

        注意：此操作不可逆，数据将被永久移除。
        """
        db.session.delete(self)   # 从数据库会话中标记删除
        db.session.commit()       # 提交事务，执行删除

    def to_dict(self):
        """
        将角色实例转换为字典格式

        用于序列化展示，便于 JSON 序列化返回给前端。

        返回:
            dict: 包含角色关键信息的字典，结构如下：
                - id: 角色唯一标识符
                - name: 角色名称
                - prompt: 系统提示词
                - icon: 角色图标
                - is_builtin: 是否为内置角色
                - created_at: 创建时间（ISO 格式字符串，可能为 None）
        """
        return {
            "id": self.id,                                  # 角色 ID
            "name": self.name,                              # 角色名称
            "prompt": self.prompt,                          # 系统提示词
            "icon": self.icon,                              # 角色图标
            "is_builtin": self.is_builtin,                  # 是否内置角色
            "created_at": self.created_at.isoformat() if self.created_at else None,  # 创建时间
        }
