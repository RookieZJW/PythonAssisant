from app.extensions import db
from datetime import datetime
import uuid


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(64), primary_key=True)
    api_key = db.Column(db.String(64), unique=True, nullable=False)
    quota = db.Column(db.Integer, default=1000)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 注意: user_id in conversations 是字符串标识符，非外键约束
    # 如需关联查询，直接使用 Conversation.query.filter_by(user_id=...)

    @classmethod
    def find_by_api_key(cls, api_key):
        return cls.query.filter_by(api_key=api_key).first()

    @classmethod
    def create_user(cls, api_key=None):
        user_id = str(uuid.uuid4())
        if api_key is None:
            api_key = str(uuid.uuid4()).replace('-', '')
        user = cls(id=user_id, api_key=api_key)
        db.session.add(user)
        db.session.commit()
        return user

    def to_dict(self):
        return {
            "id": self.id,
            "quota": self.quota,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
