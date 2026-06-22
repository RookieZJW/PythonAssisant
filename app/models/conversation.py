# -*- coding: utf-8 -*-
"""
会话（Conversation）模型模块

本模块定义了 Conversation 数据库模型，用于存储和管理用户与大语言模型之间的
每一次对话会话。每个会话可以包含多条消息，并且可以关联到特定的用户和角色。
"""

from app.extensions import db          # 导入 Flask-SQLAlchemy 数据库扩展实例
from app.models.message import Message  # 导入消息模型，用于建立会话与消息的关系
from datetime import datetime           # 导入 datetime 用于处理时间戳
import uuid                             # 导入 uuid 用于生成唯一标识符


class Conversation(db.Model):
    """
    会话模型类

    对应数据库中的 'conversations' 表，用于存储每一次对话会话的元信息。
    每个会话包含标题、关联用户、使用的模型、关联的角色等字段，
    并且通过关系（relationship）与多条消息（Message）建立一对多关联。

    属性:
        id: 会话唯一标识符（UUID 字符串，主键）
        title: 会话标题
        user_id: 关联的用户标识符
        model: 本次会话所使用的 AI 模型名称
        role_id: 关联的自定义角色 ID（可为空）
        created_at: 会话创建时间戳
        updated_at: 会话最后更新时间戳（自动更新）
        messages: 与该会话关联的所有消息列表（按创建时间升序排列）
    """
    __tablename__ = 'conversations'

    # ---- 数据库字段定义 ----
    # 会话 ID：使用 UUID 生成 36 位字符串作为主键
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 会话标题：最大长度 200 字符，不允许为空，默认值为"新对话"
    title = db.Column(db.String(200), nullable=False, default="新对话")
    # 用户 ID：最大长度 64 字符，建立数据库索引以加速按用户的查询，默认值为 "anonymous"
    user_id = db.Column(db.String(64), index=True, default="anonymous")
    # 模型名称：最大长度 32 字符，表示本次对话使用的 AI 模型（如 deepseek、gpt-4 等）
    model = db.Column(db.String(32), default="deepseek")
    # 角色 ID：最大长度 36 字符，关联到自定义角色的 ID，可为空
    role_id = db.Column(db.String(36), nullable=True, default=None)
    # 创建时间：默认值为当前 UTC 时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # 更新时间：创建时默认为当前时间，每次更新记录时自动刷新为当前时间
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ---- 关系定义 ----
    # 一对多关系：一个会话可以包含多条消息
    # backref='conversation' 允许从 Message 实例通过 .conversation 反向访问所属会话
    # lazy=True 表示延迟加载，仅在访问时才执行查询
    # order_by 指定消息按 created_at 升序排列
    messages = db.relationship(
        'Message',
        backref='conversation',
        lazy=True,
        order_by='Message.created_at.asc()'
    )

    @classmethod
    def create(cls, title="新对话", model="deepseek", user_id="anonymous", role_id=None):
        """
        创建新的会话记录

        这是一个类方法，用于快捷创建并持久化一个新的会话到数据库中。

        参数:
            title (str): 会话标题，默认为"新对话"
            model (str): 使用的 AI 模型名称，默认为 "deepseek"
            user_id (str): 用户标识符，默认为 "anonymous"
            role_id (str, optional): 关联的角色 ID，默认为 None（不使用自定义角色）

        返回:
            Conversation: 新创建并已持久化的会话实例
        """
        # 构造 Conversation 实例
        conversation = cls(
            title=title,
            model=model,
            user_id=user_id,
            role_id=role_id,
        )
        # 添加到数据库会话并提交事务
        db.session.add(conversation)
        db.session.commit()
        return conversation

    @classmethod
    def get_or_create(cls, conversation_id, role_id=None):
        """
        获取指定 ID 的会话，若不存在则创建新会话

        这是一个类方法，实现了"获取或创建"模式。如果提供了有效的会话 ID
        且该会话存在于数据库中，则返回已有会话；否则创建一个新的会话。

        参数:
            conversation_id (str): 要获取的会话 ID
            role_id (str, optional): 创建新会话时使用的角色 ID

        返回:
            Conversation: 找到的已有会话或新创建的会话实例
        """
        # 获取或创建会话
        # 如果提供了有效的会话 ID 且不是默认值 "default"
        if conversation_id and conversation_id != "default":
            # 按主键查询会话
            conversation = cls.query.filter_by(id=conversation_id).first()
            if conversation:
                return conversation

        # 未找到有效会话，创建新的会话
        return cls.create(role_id=role_id)

    @classmethod
    def get_list(cls, user_id="anonymous", page=1, page_size=20):
        """
        获取指定用户的会话列表（支持分页）

        这是一个类方法，用于查询指定用户的所有会话，按更新时间降序排列，
        并支持分页返回结果。

        参数:
            user_id (str): 用户标识符，默认为 "anonymous"
            page (int): 页码，从 1 开始，默认为 1
            page_size (int): 每页显示的记录数，默认为 20

        返回:
            dict: 包含分页信息的字典，结构如下：
                - total (int): 符合条件的会话总数
                - page (int): 当前页码
                - page_size (int): 每页大小
                - items (list): 当前页的会话字典列表（每个元素由 to_dict() 生成）
        """
        # 构建查询：按用户 ID 过滤，按更新时间降序排列（最新的在前）
        query = cls.query.filter_by(user_id=user_id).order_by(cls.updated_at.desc())

        # 计算总数
        total = query.count()
        # 执行分页查询：跳过多余的记录，限制返回数量
        conversations = query.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,           # 总记录数
            "page": page,             # 当前页码
            "page_size": page_size,   # 每页大小
            "items": [c.to_dict() for c in conversations],  # 当前页数据
        }

    def hard_delete(self):
        """
        硬删除当前会话及其所有关联消息

        此方法会从数据库中永久删除当前会话记录，同时也会删除该会话下的
        所有关联消息（通过会话 ID 在 messages 表中进行批量删除）。

        注意：此操作不可逆，数据将被永久移除。
        """
        # 先删除该会话下的所有关联消息
        Message.query.filter_by(conversation_id=self.id).delete()
        # 删除会话本身
        db.session.delete(self)
        # 提交事务
        db.session.commit()

    def to_dict(self):
        """
        将会话实例转换为字典格式

        用于序列化展示，便于 JSON 序列化返回给前端。

        返回:
            dict: 包含会话关键信息的字典，结构如下：
                - id: 会话唯一标识符
                - title: 会话标题
                - model: 使用的 AI 模型
                - role_id: 关联的角色 ID
                - created_at: 创建时间（ISO 格式字符串，可能为 None）
                - updated_at: 最后更新时间（ISO 格式字符串，可能为 None）
        """
        return {
            "id": self.id,                                  # 会话 ID
            "title": self.title,                            # 会话标题
            "model": self.model,                            # 使用的模型
            "role_id": self.role_id,                        # 关联角色 ID
            "created_at": self.created_at.isoformat() if self.created_at else None,  # 创建时间
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,  # 更新时间
        }
