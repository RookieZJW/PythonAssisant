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
    api_key = db.Column(db.String(64), unique=True, nullable=True)
    quota = db.Column(db.Integer, default=1000)
    vip_level = db.Column(db.Integer, default=0)           # 0=免费 1=VIP月卡 2=VIP年卡
    vip_expire = db.Column(db.DateTime, nullable=True)      # VIP到期时间
    daily_chat_count = db.Column(db.Integer, default=0)     # 今日对话次数
    daily_chat_date = db.Column(db.Date, nullable=True)     # 计数日期
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

    # ---- 会员系统 ----
    FREE_DAILY_LIMIT = 30  # 免费用户每日限制

    @property
    def is_vip(self):
        """是否VIP（未过期）"""
        return self.vip_level > 0 and (not self.vip_expire or self.vip_expire > datetime.utcnow())

    def can_chat_today(self):
        """今天是否还能对话"""
        if self.is_vip: return True, 9999
        today = datetime.utcnow().date()
        if self.daily_chat_date != today:
            self.daily_chat_count = 0
            self.daily_chat_date = today
            db.session.commit()
        remaining = self.FREE_DAILY_LIMIT - self.daily_chat_count
        return remaining > 0, max(0, remaining)

    def record_chat(self):
        """记录一次对话"""
        today = datetime.utcnow().date()
        if self.daily_chat_date != today:
            self.daily_chat_count = 1
            self.daily_chat_date = today
        else:
            self.daily_chat_count += 1
        db.session.commit()

    @classmethod
    def upgrade_vip(cls, user_id, days=30):
        """升级VIP"""
        user = cls.query.get(user_id)
        if not user: return None
        from datetime import timedelta
        user.vip_level = 1
        expire = datetime.utcnow() + timedelta(days=days)
        if user.vip_expire and user.vip_expire > datetime.utcnow():
            expire = user.vip_expire + timedelta(days=days)
        user.vip_expire = expire
        db.session.commit()
        return user

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "phone": self.phone,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "quota": self.quota,
            "has_password": bool(self.password_hash),
            "vip_level": self.vip_level,
            "vip_expire": self.vip_expire.isoformat() if self.vip_expire else None,
            "is_vip": self.is_vip,
            "daily_remaining": max(0, self.FREE_DAILY_LIMIT - (self.daily_chat_count if self.daily_chat_date == datetime.utcnow().date() else 0)),
            "has_wechat": bool(self.wechat_openid),
            "has_qq": bool(self.qq_openid),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
