from app.extensions import db
from app.models.message import Message
from datetime import datetime
import uuid


class Conversation(db.Model):
    __tablename__ = 'conversations'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False, default="新对话")
    user_id = db.Column(db.String(64), index=True, default="anonymous")
    model = db.Column(db.String(32), default="deepseek")
    role_id = db.Column(db.String(36), nullable=True, default=None)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = db.relationship(
        'Message',
        backref='conversation',
        lazy=True,
        order_by='Message.created_at.asc()'
    )

    @classmethod
    def create(cls, title="新对话", model="deepseek", user_id="anonymous", role_id=None):
        conversation = cls(
            title=title,
            model=model,
            user_id=user_id,
            role_id=role_id,
        )
        db.session.add(conversation)
        db.session.commit()
        return conversation

    @classmethod
    def get_or_create(cls, conversation_id, role_id=None):
        """获取或创建会话"""
        if conversation_id and conversation_id != "default":
            conversation = cls.query.filter_by(id=conversation_id).first()
            if conversation:
                return conversation

        return cls.create(role_id=role_id)

    @classmethod
    def get_list(cls, user_id="anonymous", page=1, page_size=20):
        """获取会话列表"""
        query = cls.query.filter_by(user_id=user_id).order_by(cls.updated_at.desc())

        total = query.count()
        conversations = query.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [c.to_dict() for c in conversations],
        }

    def hard_delete(self):
        """硬删除会话及所有关联消息"""
        Message.query.filter_by(conversation_id=self.id).delete()
        db.session.delete(self)
        db.session.commit()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "model": self.model,
            "role_id": self.role_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
