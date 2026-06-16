"""自定义角色模型"""
from app.extensions import db
from datetime import datetime
import uuid


class Role(db.Model):
    __tablename__ = 'roles'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(10), default='🤖')
    is_builtin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def create(cls, name, prompt, icon='🤖'):
        role = cls(name=name, prompt=prompt, icon=icon, is_builtin=False)
        db.session.add(role)
        db.session.commit()
        return role

    @classmethod
    def get_all(cls):
        return cls.query.order_by(cls.is_builtin.desc(), cls.created_at.asc()).all()

    @classmethod
    def get_by_id(cls, role_id):
        return cls.query.get(role_id)

    def update(self, name=None, prompt=None, icon=None):
        if name: self.name = name
        if prompt: self.prompt = prompt
        if icon: self.icon = icon
        db.session.commit()
        return self

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "prompt": self.prompt,
            "icon": self.icon,
            "is_builtin": self.is_builtin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
