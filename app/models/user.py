# -*- coding: utf-8 -*-
"""
用户（User）模型模块

本模块定义了 User 数据库模型，用于存储和管理系统用户信息。
用户通过 API 密钥进行身份认证，每个用户拥有一个配额（quota），
用于限制可消耗的 Token 数量。
"""

from app.extensions import db          # 导入 Flask-SQLAlchemy 数据库扩展实例
from datetime import datetime           # 导入 datetime 用于处理时间戳
import uuid                             # 导入 uuid 用于生成唯一标识符


class User(db.Model):
    """
    用户模型类

    对应数据库中的 'users' 表，用于存储用户认证信息和配额管理。
    用户通过 API 密钥（api_key）进行身份验证，每个用户有独立的
    调用配额限制。

    属性:
        id: 用户唯一标识符（UUID 字符串，主键）
        api_key: API 密钥（唯一且不可为空），用于身份认证
        quota: 用户的 Token 配额上限，默认为 1000
        created_at: 用户创建时间戳

    注意:
        - conversations 表中的 user_id 字段仅为字符串标识符，
          并未建立外键约束（允许自由关联任意用户 ID）。
        - 如需按用户查询会话，应直接使用
          Conversation.query.filter_by(user_id=...) 进行过滤查询。
    """
    __tablename__ = 'users'

    # ---- 数据库字段定义 ----
    # 用户 ID：字符串类型（64 位长度）作为主键，使用 UUID 生成
    id = db.Column(db.String(64), primary_key=True)
    # API 密钥：最大长度 64 字符，唯一约束（不允许重复），不允许为空
    api_key = db.Column(db.String(64), unique=True, nullable=False)
    # 配额：整型数值，表示用户的 Token 消耗上限，默认为 1000
    quota = db.Column(db.Integer, default=1000)
    # 创建时间：默认值为当前 UTC 时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 注意: 会话表（conversations）中的 user_id 字段是独立的字符串标识符，
    #       并未与此表建立外键约束。这种设计提供了更大的灵活性，允许
    #       在未创建用户记录的情况下仍能创建会话。
    # 如需进行用户与会话的关联查询，直接使用：
    #   Conversation.query.filter_by(user_id=...)

    @classmethod
    def find_by_api_key(cls, api_key):
        """
        根据 API 密钥查找用户

        这是一个类方法，通过 API 密钥查询对应的用户记录。
        用于 API 请求认证环节，验证请求方是否拥有有效的 API 密钥。

        参数:
            api_key (str): 要查询的 API 密钥字符串

        返回:
            User or None: 找到的用户实例，若密钥不存在则返回 None
        """
        # 按 api_key 精确匹配查询，返回第一个匹配结果
        return cls.query.filter_by(api_key=api_key).first()

    @classmethod
    def create_user(cls, api_key=None):
        """
        创建新用户

        这是一个类方法，用于创建并持久化一个新的用户记录。
        如果未提供 api_key，则自动生成一个不含连字符的 UUID 作为密钥。

        参数:
            api_key (str, optional): 自定义 API 密钥，若不提供则自动生成

        返回:
            User: 新创建并已持久化的用户实例
        """
        # 生成唯一的用户 ID（UUID 字符串）
        user_id = str(uuid.uuid4())
        # 如果未提供 API 密钥，则自动生成一个（移除 UUID 中的连字符）
        if api_key is None:
            api_key = str(uuid.uuid4()).replace('-', '')
        # 构造 User 实例（配额使用默认值 1000）
        user = cls(id=user_id, api_key=api_key)
        # 添加到数据库会话并提交事务
        db.session.add(user)
        db.session.commit()
        return user

    def to_dict(self):
        """
        将用户实例转换为字典格式

        用于序列化展示，便于 JSON 序列化返回给前端。
        注意：出于安全考虑，返回的字典中不包含 api_key 字段，
        以避免泄露用户的 API 凭证信息。

        返回:
            dict: 包含用户公开信息的字典，结构如下：
                - id: 用户唯一标识符
                - quota: 用户的 Token 配额
                - created_at: 创建时间（ISO 格式字符串，可能为 None）
        """
        return {
            "id": self.id,                                  # 用户 ID
            "quota": self.quota,                            # 用户配额
            "created_at": self.created_at.isoformat() if self.created_at else None,  # 创建时间
        }
