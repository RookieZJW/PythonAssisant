"""登录/注册 API — 密码 + 手机验证码 + 微信/QQ 扫码"""
import random
import json
from datetime import datetime
from app.config.settings import settings
from flask import Blueprint, request, session
from app.models.user import User
from app.extensions import db
from app.utils.response import success, error

auth_bp = Blueprint('auth', __name__)

def send_aliyun_sms(phone, code):
    """??????? API ?????"""
    from alibabacloud_dysmsapi20170525.client import Client
    from alibabacloud_dysmsapi20170525 import models as dysms_models
    from alibabacloud_tea_openapi import models as open_api_models

    config = open_api_models.Config(
        access_key_id=settings.ALIYUN_SMS_ACCESS_KEY_ID,
        access_key_secret=settings.ALIYUN_SMS_ACCESS_KEY_SECRET
    )
    config.endpoint = "dysmsapi.aliyuncs.com"
    client = Client(config)

    req = dysms_models.SendSmsRequest(
        phone_numbers=phone,
        sign_name=settings.ALIYUN_SMS_SIGN_NAME,
        template_code=settings.ALIYUN_SMS_TEMPLATE_CODE,
        template_param=json.dumps({"code": code}, ensure_ascii=False)
    )
    resp = client.send_sms(req)
    body = resp.body
    if body.code != "OK":
        raise RuntimeError(f"????? {body.code}: {body.message}")

# 测试模式：验证码固定为 123456（生产环境需接入阿里云/腾讯云短信服务）
SMS_CONFIGURED = bool(
    settings.ALIYUN_SMS_ACCESS_KEY_ID
    and settings.ALIYUN_SMS_ACCESS_KEY_SECRET
    and settings.ALIYUN_SMS_SIGN_NAME
    and settings.ALIYUN_SMS_TEMPLATE_CODE
)
sms_codes = {}  # {phone: (code, sent_at)}


@auth_bp.route('/auth/register', methods=['POST'])
def register():
    """用户名+密码注册"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    nickname = data.get('nickname', '').strip() or username

    if not username or len(username) < 2: return error("用户名至少2位", 400)
    if not password or len(password) < 6: return error("密码至少6位", 400)

    user, err = User.register_username(username, password, nickname)
    if err: return error(err, 409)

    session['user_id'] = user.id
    return success(user.to_dict(), "注册成功")


@auth_bp.route('/auth/login', methods=['POST'])
def login():
    """用户名+密码登录"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password: return error("请输入用户名和密码", 400)

    user, err = User.login_username(username, password)
    if err: return error(err, 401)

    session['user_id'] = user.id
    return success(user.to_dict(), "登录成功")


@auth_bp.route('/auth/sms/send', methods=['POST'])
def sms_send():
    """??????????????"""
    data = request.get_json() or {}
    phone = data.get('phone', '').strip()
    if not phone or not phone.isdigit() or len(phone) != 11 or not phone.startswith('1'):
        return error("????????", 400)

    now = datetime.utcnow()
    saved = sms_codes.get(phone)
    if saved and (now - saved[1]).total_seconds() < 60:
        return error("???????????60????", 429)

    code = str(random.randint(100000, 999999))
    if SMS_CONFIGURED:
        try:
            send_aliyun_sms(phone, code)
        except Exception as e:
            return error(f"??????: {str(e)}", 500)
    else:
        code = '123456'
        print(f"[SMS][????] ??? {phone} ??? {code}")

    sms_codes[phone] = (code, now)
    msg = "??????"
    if not SMS_CONFIGURED:
        msg += "?????????123456?"
    return success(None, msg)


@auth_bp.route('/auth/sms/login', methods=['POST'])
def sms_login():
    """??? + ?????/??"""
    data = request.get_json() or {}
    phone = data.get('phone', '').strip()
    code = data.get('code', '').strip()
    if not phone or not code:
        return error("??????????", 400)

    saved = sms_codes.get(phone)
    if not saved:
        return error("???????", 400)
    saved_code, sent_at = saved
    if (datetime.utcnow() - sent_at).total_seconds() > 300:
        sms_codes.pop(phone, None)
        return error("????????????", 401)
    if code != saved_code:
        return error("?????", 401)

    sms_codes.pop(phone, None)

    user = User.query.filter_by(phone=phone).first()
    if not user:
        user, _ = User.register_phone(phone)
    session['user_id'] = user.id
    return success(user.to_dict(), "????")


@auth_bp.route('/auth/wechat/qrcode', methods=['GET'])
def wechat_qrcode():
    """微信扫码登录 — 返回二维码 URL (需要微信开放平台资质)"""
    return success({
        "type": "wechat",
        "note": "微信扫码登录需要企业资质认证。目前为演示模式。",
        "guide": "1. 前往 open.weixin.qq.com 注册开发者账号\n2. 创建网站应用获取 AppID/AppSecret\n3. 配置回调域名\n4. 替换本接口中的 OAuth URL",
    })


@auth_bp.route('/auth/qq/qrcode', methods=['GET'])
def qq_qrcode():
    """QQ 扫码登录 — 返回二维码 URL (需要 QQ 互联资质)"""
    return success({
        "type": "qq",
        "note": "QQ扫码登录需要QQ互联平台认证。目前为演示模式。",
        "guide": "1. 前往 connect.qq.com 注册开发者\n2. 创建应用获取 APP_ID/APP_KEY\n3. 配置回调地址\n4. 替换本接口中的 OAuth URL",
    })


@auth_bp.route('/auth/me', methods=['GET'])
def me():
    """获取当前登录用户信息"""
    uid = session.get('user_id')
    if not uid: return error("未登录", 401)
    user = User.find_by_id(uid)
    if not user: return error("用户不存在", 404)
    return success(user.to_dict())


@auth_bp.route('/auth/logout', methods=['POST'])
def logout():
    """退出登录"""
    session.clear()
    return success(None, "已退出")


# ---- 会员/VIP 管理 ----
@auth_bp.route('/vip/upgrade', methods=['POST'])
def vip_upgrade():
    """升级VIP（管理接口，生产环境需加管理员权限）"""
    data = request.get_json() or {}
    user_id = data.get('user_id') or session.get('user_id','')
    days = data.get('days', 30)
    user = User.upgrade_vip(user_id, days)
    if not user: return error("用户不存在", 404)
    return success(user.to_dict(), f"已升级VIP，有效期至 {user.vip_expire.strftime('%Y-%m-%d')}")

@auth_bp.route('/vip/stats', methods=['GET'])
def vip_stats():
    """查询当前用户用量"""
    uid = session.get('user_id','')
    if not uid: return error("未登录", 401)
    user = User.find_by_id(uid)
    if not user: return error("用户不存在", 404)
    can, remain = user.can_chat_today()
    return success({
        "is_vip": user.is_vip,
        "vip_level": user.vip_level,
        "vip_expire": user.vip_expire.isoformat() if user.vip_expire else None,
        "daily_used": user.daily_chat_count,
        "daily_limit": user.FREE_DAILY_LIMIT,
        "daily_remaining": remain,
        "can_chat": can,
    })


@auth_bp.route('/auth/update-profile', methods=['PUT'])
def update_profile():
    """修改昵称/密码"""
    uid = session.get('user_id')
    if not uid: return error("未登录", 401)
    user = User.find_by_id(uid)
    if not user: return error("用户不存在", 404)

    data = request.get_json() or {}
    if data.get('nickname'):
        user.nickname = data['nickname'].strip()
    if data.get('avatar'):
        user.avatar = data['avatar'].strip()
    if data.get('new_password'):
        if not user.check_password(data.get('old_password', '')):
            return error("原密码错误", 400)
        user.password_hash = User.hash_password(data['new_password'].strip())

    db.session.commit()
    return success(user.to_dict(), "更新成功")
