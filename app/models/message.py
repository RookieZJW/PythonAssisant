import re
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
    def create(cls, conversation_id, role, content, tokens=None):
        if tokens is None:
            tokens = cls._estimate_tokens(content)
        message = cls(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tokens=tokens,
        )
        db.session.add(message)
        db.session.commit()
        return message

    @staticmethod
    def _estimate_tokens(text):
        """估算 Token 数（中文字符~1.5，英文词~1.3）"""
        import re
        if not text: return 0
        chinese = len(re.findall(r'[一-鿿＀-￯]', text))
        english = len(re.findall(r'[a-zA-Z]+', text))
        numbers = len(re.findall(r'\d+', text))
        other = max(0, len(text) - chinese - english - numbers)
        return max(1, int(chinese * 1.5 + english * 0.3 + numbers * 0.5 + other))


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
