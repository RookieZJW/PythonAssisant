# -*- coding: utf-8 -*-
"""
消息（Message）模型模块

本模块定义了 Message 数据库模型，用于存储对话中的每一条消息记录。
每条消息都属于一个特定的会话（Conversation），包含消息角色（用户/助手/系统）、
消息内容以及估算的 Token 数量等信息。
"""

import re                              # 导入正则表达式模块，用于文本处理和 Token 估算
from app.extensions import db          # 导入 Flask-SQLAlchemy 数据库扩展实例
from datetime import datetime           # 导入 datetime 用于处理时间戳


class Message(db.Model):
    """
    消息模型类

    对应数据库中的 'messages' 表，用于存储对话会话中的每一条消息记录。
    每条消息关联到一个会话（通过外键 conversation_id），并记录消息的
    发送角色、文本内容和估算的 Token 消耗量。

    属性:
        id: 消息唯一标识符（自增整数，主键）
        conversation_id: 所属会话的外键 ID（关联 conversations 表）
        role: 消息发送角色（user/assistant/system）
        content: 消息正文内容（文本类型）
        tokens: 消息消耗的 Token 估算值
        created_at: 消息创建时间戳
    """
    __tablename__ = 'messages'

    # ---- 数据库字段定义 ----
    # 消息 ID：自增整数作为主键
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 所属会话 ID：外键关联到 conversations 表的 id 字段
    # 类型为字符串（36 位 UUID），不允许为空，并建立数据库索引以加速查询
    conversation_id = db.Column(
        db.String(36),
        db.ForeignKey('conversations.id'),  # 外键约束，引用 conversations.id
        nullable=False,                      # 不允许为空
        index=True                           # 建立索引以加速按会话查询消息
    )
    # 消息角色：最大长度 16 字符，标识消息发送者身份，通常为 "user"、"assistant" 或 "system"
    role = db.Column(db.String(16), nullable=False)  # user / assistant / system
    # 消息内容：使用 Text 类型存储较长的文本内容，不允许为空
    content = db.Column(db.Text, nullable=False)
    # Token 数：估算的消息 Token 消耗量，默认为 0
    tokens = db.Column(db.Integer, default=0)
    # 创建时间：默认值为当前 UTC 时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def create(cls, conversation_id, role, content, tokens=None):
        """
        创建新的消息记录

        这是一个类方法，用于创建并持久化一条新消息到数据库中。
        如果未显式提供 tokens 参数，则调用 _estimate_tokens() 方法
        根据消息内容自动估算 Token 消耗量。

        参数:
            conversation_id (str): 消息所属的会话 ID
            role (str): 消息发送角色，如 "user"、"assistant"、"system"
            content (str): 消息文本内容
            tokens (int, optional): 消息的 Token 数。若为 None，则自动估算

        返回:
            Message: 新创建并已持久化的消息实例
        """
        # 如果没有提供 tokens，则根据内容自动估算 Token 数
        if tokens is None:
            tokens = cls._estimate_tokens(content)
        # 构造 Message 实例
        message = cls(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tokens=tokens,
        )
        # 添加到数据库会话并提交事务
        db.session.add(message)
        db.session.commit()
        return message

    @staticmethod
    def _estimate_tokens(text):
        """
        估算文本的 Token 消耗数（私有静态方法）

        根据不同语言字符类型的经验比例来估算 Token 数量：
        - 中文字符：每个约 1.5 个 Token
        - 英文单词：每个约 0.3 个 Token
        - 数字序列：每个约 0.5 个 Token
        - 其他字符：每个约 1.0 个 Token（标点、空格、特殊符号等）

        参数:
            text (str): 要估算的文本内容

        返回:
            int: 估算的 Token 数量，至少为 1
        """
        import re
        # 处理空文本情况
        if not text: return 0

        # 统计中文字符数量（Unicode 范围：一-鿿 和 ＀-￯）
        chinese = len(re.findall(r'[一-鿿＀-￯]', text))
        # 统计英文单词数量（连续的字母序列计为一个词）
        english = len(re.findall(r'[a-zA-Z]+', text))
        # 统计数字序列数量（连续的数字序列计为一个）
        numbers = len(re.findall(r'\d+', text))
        # 其余字符（标点符号、空格、特殊字符等）
        other = max(0, len(text) - chinese - english - numbers)

        # 按经验比例计算并返回 Token 数，至少返回 1
        return max(1, int(chinese * 1.5 + english * 0.3 + numbers * 0.5 + other))


    @classmethod
    def get_history(cls, conversation_id, limit=20):
        """
        获取指定会话的历史消息列表

        这是一个类方法，用于查询某个会话的历史消息记录，
        按创建时间升序排列，并支持限制返回条数。

        参数:
            conversation_id (str): 会话 ID
            limit (int): 最大返回的消息数量，默认为 20 条

        返回:
            list: 消息字典列表，每个元素由 to_dict() 生成，
                  结构为 {"role": 角色, "content": 内容}
        """
        # 按会话 ID 过滤，按创建时间升序排列，限制返回条数
        messages = cls.query.filter_by(conversation_id=conversation_id) \
            .order_by(cls.created_at.asc()) \
            .limit(limit) \
            .all()
        # 将每条消息转换为字典格式后返回
        return [m.to_dict() for m in messages]

    def to_dict(self):
        """
        将消息实例转换为字典格式（用于 API 输出）

        序列化为字典，便于 JSON 序列化后返回给前端或 AI 模型 API。
        注意：此方法仅返回 role 和 content 两个关键字段，
        不包含 ID、tokens 等内部信息。

        返回:
            dict: 包含消息角色和内容的字典，结构如下：
                - role: 消息发送角色（user/assistant/system）
                - content: 消息文本内容
        """
        return {
            "role": self.role,          # 消息角色：user / assistant / system
            "content": self.content,    # 消息文本内容
        }
