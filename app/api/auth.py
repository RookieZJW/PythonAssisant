"""登录/注册 API — 密码 + 手机验证码 + 微信/QQ 扫码"""
import random
from flask import Blueprint, request, session
from app.models.user import User
from app.extensions import db
from app.utils.response import success, error

auth_bp = Blueprint('auth', __name__)

# 测试模式：验证码固定为 123456（生产环境需接入阿里云/腾讯云短信服务）
SMS_TEST_MODE = True
sms_codes = {}  # {phone: code}


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
    """发送短信验证码"""
    data = request.get_json() or {}
    phone = data.get('phone', '').strip()
    if not phone or len(phone) < 11: return error("请输入有效手机号", 400)

    if SMS_TEST_MODE:
        code = '123456'
    else:
        code = str(random.randint(100000, 999999))
        # TODO: 调用阿里云/腾讯云短信 API 发送 code 到 phone

    sms_codes[phone] = code
    print(f"[SMS] 手机号 {phone} 验证码: {code}")  # 生产环境删除此行
    return success(None, "验证码已发送" + ("(测试: 123456)" if SMS_TEST_MODE else ""))


@auth_bp.route('/auth/sms/login', methods=['POST'])
def sms_login():
    """手机号+验证码登录/注册"""
    data = request.get_json() or {}
    phone = data.get('phone', '').strip()
    code = data.get('code', '').strip()
    if not phone or not code: return error("请输入手机号和验证码", 400)

    saved = sms_codes.get(phone, '')
    if code != saved and not SMS_TEST_MODE:
        return error("验证码错误", 401)

    # 验证码正确，清除
    sms_codes.pop(phone, None)

    user = User.query.filter_by(phone=phone).first()
    if not user:
        user, _ = User.register_phone(phone)

    session['user_id'] = user.id
    return success(user.to_dict(), "登录成功")


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
