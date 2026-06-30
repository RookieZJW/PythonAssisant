"""自定义背景历史模型"""
from app.extensions import db
from datetime import datetime
import uuid


class Background(db.Model):
    __tablename__ = 'backgrounds'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    url = db.Column(db.Text, nullable=False)
    bg_type = db.Column(db.String(10), default='image')  # image / video
    mode = db.Column(db.String(10), default='full')       # full / chat
    size = db.Column(db.String(20), default='cover')      # cover / contain / auto / 100% 100%
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def add(cls, url, bg_type='image', mode='full', size='cover', user_id=None):
        # 去重：相同 URL + 相同用户不重复添加
        existing = cls.query.filter_by(url=url, user_id=user_id).first()
        if existing:
            existing.bg_type = bg_type
            existing.mode = mode
            existing.size = size
            existing.created_at = datetime.utcnow()
            db.session.commit()
            return existing

        bg = cls(url=url, bg_type=bg_type, mode=mode, size=size, user_id=user_id)
        db.session.add(bg)
        db.session.commit()
        return bg

    @classmethod
    def get_all(cls):
        return cls.query.order_by(cls.created_at.desc()).limit(20).all()

    @classmethod
    def delete_by_id(cls, bg_id):
        bg = cls.query.get(bg_id)
        if bg:
            db.session.delete(bg)
            db.session.commit()

    def to_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "bg_type": self.bg_type,
            "mode": self.mode,
            "size": self.size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
