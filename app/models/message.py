from app.extensions import db
from datetime import datetime


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    conversation_id = db.Column(
        db.String(36),
        db.ForeignKey('conversations.id'),
        nullable=False,
        index=True
    )
    role = db.Column(db.String(16), nullable=False)  # user / assistant / system
    content = db.Column(db.Text, nullable=False)
    tokens = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def create(cls, conversation_id, role, content, tokens=0):
        message = cls(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tokens=tokens,
        )
        db.session.add(message)
        db.session.commit()
        return message

    @classmethod
    def get_history(cls, conversation_id, limit=20):
        """获取会话历史消息"""
        messages = cls.query.filter_by(conversation_id=conversation_id) \
            .order_by(cls.created_at.asc()) \
            .limit(limit) \
            .all()
        return [m.to_dict() for m in messages]

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
        }
