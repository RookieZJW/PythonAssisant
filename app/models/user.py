"""用户模型 — 支持密码登录、手机验证码、微信/QQ 扫码登录"""
import bcrypt
from app.extensions import db
from datetime import datetime
import uuid


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), unique=True, nullable=True)       # 用户名 (密码登录)
    password_hash = db.Column(db.String(200), nullable=True)              # bcrypt 密码哈希
    phone = db.Column(db.String(20), unique=True, nullable=True)           # 手机号 (短信登录)
    wechat_openid = db.Column(db.String(100), unique=True, nullable=True)  # 微信 OpenID
    qq_openid = db.Column(db.String(100), unique=True, nullable=True)      # QQ OpenID
    nickname = db.Column(db.String(50), default="用户")                     # 昵称
    avatar = db.Column(db.String(200), default="")                         # 头像 URL
    api_key = db.Column(db.String(64), unique=True, nullable=True)         # API Key (兼容旧版)
    quota = db.Column(db.Integer, default=1000)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ---- 密码相关 ----
    @staticmethod
    def hash_password(password):
        """对密码进行 bcrypt 哈希"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        """验证密码"""
        if not self.password_hash: return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    # ---- 注册/查找 ----
    @classmethod
    def register_username(cls, username, password, nickname=None):
        """用户名+密码注册"""
        if cls.query.filter_by(username=username).first():
            return None, "用户名已存在"
        user = cls(
            username=username,
            password_hash=cls.hash_password(password),
            nickname=nickname or username,
        )
        db.session.add(user)
        db.session.commit()
        return user, None

    @classmethod
    def register_phone(cls, phone, password=None, nickname=None):
        """手机号注册（可选密码）"""
        if cls.query.filter_by(phone=phone).first():
            return None, "手机号已注册"
        user = cls(
            phone=phone,
            password_hash=cls.hash_password(password) if password else None,
            nickname=nickname or f"用户{phone[-4:]}",
        )
        db.session.add(user)
        db.session.commit()
        return user, None

    @classmethod
    def login_username(cls, username, password):
        """用户名密码登录"""
        user = cls.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return None, "用户名或密码错误"
        return user, None

    @classmethod
    def login_phone(cls, phone):
        """手机号登录（验证码已验证通过）"""
        user = cls.query.filter_by(phone=phone).first()
        if not user:
            return None, "手机号未注册"
        return user, None

    @classmethod
    def find_by_id(cls, uid):
        return cls.query.get(uid)

    @classmethod
    def find_by_api_key(cls, api_key):
        return cls.query.filter_by(api_key=api_key).first()

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "phone": self.phone,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "quota": self.quota,
            "has_password": bool(self.password_hash),
            "has_wechat": bool(self.wechat_openid),
            "has_qq": bool(self.qq_openid),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
