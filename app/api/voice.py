"""
语音合成模块 API 路由
========================
提供文字转语音（TTS）功能，支持两种后端引擎：
- 火山引擎 TTS（ByteDance Volcano Engine）
- 腾讯云 TTS（Tencent Cloud）

主要功能：
- 将文本转换为语音音频（MP3 格式）
- 提供多款音色选择（男声、女声、童声、情感声等）
- 获取可用音色列表
"""
import base64
import requests
import hashlib
from flask import Blueprint, request
from app.config.settings import settings
from app.utils.response import success, error

# 创建名为 'voice' 的蓝图，用于组织语音合成相关的路由
voice_bp = Blueprint('voice', __name__)

# ====== 音色库定义 ======

# 火山引擎音色映射表
# key: 前端使用的音色标识符
# name: 火山引擎 API 中的音色 ID
# label: 中文显示名称
# engine: 所属引擎标识
VOLCANO_VOICES = {
    "v-xiaoyuan":  {"name": "BV700_streaming", "label": "小源 (火山·V2女声)", "engine": "volcano"},
    "v-daxia":     {"name": "BV701_streaming", "label": "大夏 (火山·V2男声)", "engine": "volcano"},
    "v-qingxin":   {"name": "BV001_streaming", "label": "清心 (火山·通用女声)", "engine": "volcano"},
    "v-zhixing":   {"name": "BV002_streaming", "label": "知行 (火山·通用男声)", "engine": "volcano"},
    "v-zhixing2":  {"name": "BV004_streaming", "label": "知性 (火山·清晰女声)", "engine": "volcano"},
    "v-tongtong":  {"name": "BV005_streaming", "label": "彤彤 (火山·童声)", "engine": "volcano"},
    "v-daqing":    {"name": "BV401_streaming", "label": "大庆 (火山·情感男声)", "engine": "volcano"},
    "v-xiaoai":    {"name": "BV402_streaming", "label": "小艾 (火山·情感女声)", "engine": "volcano"},
}

# 腾讯云音色映射表
TENCENT_VOICES = {
    "t-zhiyu":     {"name": "1001", "label": "智瑜 (腾讯·情感女声)", "engine": "tencent"},
    "t-zhimei":    {"name": "1003", "label": "智美 (腾讯·客服女声)", "engine": "tencent"},
    "t-zhiling2":  {"name": "1050", "label": "智聆 (腾讯·精品女声)", "engine": "tencent"},
}

# 合并所有音色为一个统一查找表
VOICES = {**VOLCANO_VOICES, **TENCENT_VOICES}
# 默认音色：火山引擎小源女声
DEFAULT_VOICE = "v-xiaoyuan"


# ====== TTS 引擎实现函数 ======

def _tts_volcano(text, voice):
    """
    火山引擎 TTS 调用
    --------------------
    通过火山引擎的 OpenSpeech API 将文本转为语音。
    使用 Bearer Token 认证，返回 MP3 格式的音频二进制数据。

    参数:
        text: 要合成的文本内容
        voice: 火山引擎音色 ID（如 "BV700_streaming"）

    返回:
        bytes 类型的音频数据（MP3 格式）

    抛出:
        RuntimeError: 配置缺失或 API 返回错误时抛出
    """
    # 从配置文件中获取火山引擎的认证信息
    token = settings.VOLCANO_TTS_TOKEN
    app_id = settings.VOLCANO_TTS_APP_ID
    if not token or not app_id:
        raise RuntimeError("火山引擎未配置，请在 .env 中设置 VOLCANO_TTS_TOKEN 和 VOLCANO_TTS_APP_ID")

    # 调用火山引擎 TTS API
    resp = requests.post(
        "https://openspeech.bytedance.com/api/v1/tts",
        headers={
            "Authorization": f"Bearer;{token}",
            "Content-Type": "application/json",
        },
        json={
            "app": {"appid": app_id, "token": token, "cluster": "volcano_tts"},
            "user": {"uid": "python-assistant"},
            "audio": {"voice_type": voice, "encoding": "mp3", "rate": 24000},
            "request": {"reqid": str(hash(text))[:16], "text": text, "text_type": "plain", "operation": "query"},
        },
        timeout=30
    )

    # 检查 HTTP 状态码
    if resp.status_code != 200:
        raise RuntimeError(f"火山引擎 ({resp.status_code}): {resp.text[:200]}")

    # 解析响应 JSON
    data = resp.json()
    if data.get("code") != 3000:
        raise RuntimeError(f"火山引擎: {data.get('message', 'unknown error')}")

    # 火山引擎返回的音频数据以 base64 编码存储在 data 字段中
    audio_b64 = data.get("data") or data.get("audio") or ""
    if not audio_b64:
        raise RuntimeError(f"火山引擎未返回音频: {list(data.keys())}")

    # 将 base64 解码为二进制音频数据
    return base64.b64decode(audio_b64)


def _tts_tencent(text, voice):
    """
    腾讯云 TTS 调用
    ------------------
    通过腾讯云 TTS SDK 将文本转为语音。
    使用 SecretId + SecretKey 认证，返回 MP3 格式的音频二进制数据。

    参数:
        text: 要合成的文本内容
        voice: 腾讯云音色 ID（如 "1001"）

    返回:
        bytes 类型的音频数据（MP3 格式）

    抛出:
        RuntimeError: 配置缺失或 API 返回错误时抛出
    """
    # 从配置文件中获取腾讯云的认证信息
    sid = settings.TENCENT_TTS_SECRET_ID
    skey = settings.TENCENT_TTS_SECRET_KEY
    if not sid or not skey:
        raise RuntimeError("腾讯云 TTS 未配置，请在 .env 中设置 TENCENT_TTS_SECRET_ID 和 TENCENT_TTS_SECRET_KEY")

    # 使用腾讯云 Python SDK 进行 TTS 调用
    from tencentcloud.common import credential
    from tencentcloud.tts.v20190823 import tts_client, models

    # 创建认证对象和 TTS 客户端
    cred = credential.Credential(sid, skey)
    client = tts_client.TtsClient(cred, "")
    req = models.TextToVoiceRequest()
    req.Text = text
    req.VoiceType = int(voice)
    req.SessionId = hashlib.md5(text.encode()).hexdigest()[:16]
    req.Codec = "mp3"
    req.SampleRate = 16000
    req.Volume = 5
    req.Speed = 0

    # 发送请求并获取响应
    resp = client.TextToVoice(req)
    audio_b64 = resp.Audio
    if not audio_b64:
        raise RuntimeError(f"腾讯云未返回音频")
    # 将 base64 解码为二进制音频数据
    return base64.b64decode(audio_b64)


# TTS 引擎调度表：根据引擎名称映射到对应的实现函数
TTS_ENGINES = {
    "volcano": _tts_volcano,
    "tencent": _tts_tencent,
}


# ====== API 路由 ======

@voice_bp.route('/tts', methods=['POST'])
def tts():
    """
    文字转语音接口
    -----------------
    接收文本和音色选择，调用对应的 TTS 引擎生成语音，
    以 base64 编码的 MP3 音频数据返回。

    请求体 JSON 字段:
        - text (必填): 要合成的文本，长度不超过 300 字
        - voice (可选): 音色 key，默认使用 "v-xiaoyuan"

    返回:
        JSON 响应，包含 base64 编码的音频数据和元信息
    """
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    voice_key = data.get("voice", DEFAULT_VOICE)

    # 校验文本参数
    if not text:
        return error("text 参数不能为空", 400)
    if len(text) > 300:
        return error("文本过长，请控制在 300 字以内", 400)

    # 查找音色配置
    v = VOICES.get(voice_key)
    if not v:
        return error(f"未知音色: {voice_key}", 400)

    try:
        # 根据引擎类型获取对应的 TTS 实现函数
        engine_fn = TTS_ENGINES.get(v["engine"])
        if not engine_fn:
            return error(f"未知引擎: {v['engine']}", 500)

        # 调用引擎生成语音
        audio_bytes = engine_fn(text, v["name"])
        # 将二进制音频数据编码为 base64 以便 JSON 传输
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return success({
            "audio": audio_b64,        # base64 编码的音频数据
            "format": "mp3",           # 音频格式
            "voice": v["name"],        # 引擎使用的音色 ID
            "voice_key": voice_key,    # 前端的音色标识
            "engine": v["engine"],     # 使用的引擎
            "text_length": len(text),  # 原始文本长度
        })
    except Exception as e:
        return error(f"语音合成失败: {str(e)}", 500)


@voice_bp.route('/voices', methods=['GET'])
def list_voices():
    """
    获取可用音色列表（含引擎标识）
    --------------------------------
    返回所有可用音色的 key、中文名称和所属引擎，
    供前端选择器展示。

    返回:
        JSON 响应，包含音色列表
    """
    return success([
        {"key": k, "label": v["label"], "engine": v["engine"]}
        for k, v in VOICES.items()
    ])


def register_socketio_events(socketio):
    """
    预留的 Socket.IO 事件注册函数
    ---------------------------------
    当前为空实现，后续可用于实现 WebSocket 方式的实时语音合成推送。
    """
    pass
