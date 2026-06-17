"""语音合成 (TTS) API — 火山引擎 + 腾讯云"""
import base64
import requests
import hashlib
from flask import Blueprint, request
from app.config.settings import settings
from app.utils.response import success, error

voice_bp = Blueprint('voice', __name__)

# ====== 音色库 ======
VOLCANO_VOICES = {
    "v-xiaoyuan": {"name": "BV700_streaming", "label": "小源 (火山·V2女声)", "engine": "volcano"},
    "v-daxia":   {"name": "BV701_streaming", "label": "大夏 (火山·V2男声)", "engine": "volcano"},
    "v-qingxin": {"name": "BV001_streaming", "label": "清心 (火山·通用女声)", "engine": "volcano"},
    "v-zhixing": {"name": "BV002_streaming", "label": "知行 (火山·通用男声)", "engine": "volcano"},
    "v-zhixing2":{"name": "BV004_streaming", "label": "知性 (火山·清晰女声)", "engine": "volcano"},
    "v-tongtong": {"name": "BV005_streaming", "label": "彤彤 (火山·童声)", "engine": "volcano"},
    "v-daqing":  {"name": "BV401_streaming", "label": "大庆 (火山·情感男声)", "engine": "volcano"},
    "v-xiaoai":  {"name": "BV402_streaming", "label": "小艾 (火山·情感女声)", "engine": "volcano"},
}

TENCENT_VOICES = {
    "t-zhiyu":    {"name": "1001", "label": "智瑜 (腾讯·情感女声)", "engine": "tencent"},
    "t-zhimei":   {"name": "1003", "label": "智美 (腾讯·客服女声)", "engine": "tencent"},
    "t-zhiling2": {"name": "1050", "label": "智聆 (腾讯·精品女声)", "engine": "tencent"},
}

VOICES = {**VOLCANO_VOICES, **TENCENT_VOICES}
DEFAULT_VOICE = "v-xiaoyuan"


# ====== TTS 引擎实现 ======

def _tts_volcano(text, voice):
    """火山引擎 TTS"""
    token = settings.VOLCANO_TTS_TOKEN
    app_id = settings.VOLCANO_TTS_APP_ID
    if not token or not app_id:
        raise RuntimeError("火山引擎未配置，请在 .env 中设置 VOLCANO_TTS_TOKEN 和 VOLCANO_TTS_APP_ID")

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

    if resp.status_code != 200:
        raise RuntimeError(f"火山引擎 ({resp.status_code}): {resp.text[:200]}")

    data = resp.json()
    if data.get("code") != 3000:
        raise RuntimeError(f"火山引擎: {data.get('message', 'unknown error')}")

    # 火山引擎返回 base64 在 data 字段中
    audio_b64 = data.get("data") or data.get("audio") or ""
    if not audio_b64:
        raise RuntimeError(f"火山引擎未返回音频: {list(data.keys())}")

    return base64.b64decode(audio_b64)


def _tts_tencent(text, voice):
    """腾讯云 TTS"""
    sid = settings.TENCENT_TTS_SECRET_ID
    skey = settings.TENCENT_TTS_SECRET_KEY
    if not sid or not skey:
        raise RuntimeError("腾讯云 TTS 未配置，请在 .env 中设置 TENCENT_TTS_SECRET_ID 和 TENCENT_TTS_SECRET_KEY")

    from tencentcloud.common import credential
    from tencentcloud.tts.v20190823 import tts_client, models

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

    resp = client.TextToVoice(req)
    audio_b64 = resp.Audio
    if not audio_b64:
        raise RuntimeError(f"腾讯云未返回音频")
    return base64.b64decode(audio_b64)


TTS_ENGINES = {
    "volcano": _tts_volcano,
    "tencent": _tts_tencent,
}


# ====== API ======

@voice_bp.route('/tts', methods=['POST'])
def tts():
    """
    POST /api/v1/tts
    Body: {"text": "...", "voice": "v-xiaoyuan"}
    """
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    voice_key = data.get("voice", DEFAULT_VOICE)

    if not text:
        return error("text 参数不能为空", 400)
    if len(text) > 300:
        return error("文本过长，请控制在 300 字以内", 400)

    v = VOICES.get(voice_key)
    if not v:
        return error(f"未知音色: {voice_key}", 400)

    try:
        engine_fn = TTS_ENGINES.get(v["engine"])
        if not engine_fn:
            return error(f"未知引擎: {v['engine']}", 500)

        audio_bytes = engine_fn(text, v["name"])
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return success({
            "audio": audio_b64,
            "format": "mp3",
            "voice": v["name"],
            "voice_key": voice_key,
            "engine": v["engine"],
            "text_length": len(text),
        })
    except Exception as e:
        return error(f"语音合成失败: {str(e)}", 500)


@voice_bp.route('/voices', methods=['GET'])
def list_voices():
    """获取可用音色列表（含引擎标识）"""
    return success([
        {"key": k, "label": v["label"], "engine": v["engine"]}
        for k, v in VOICES.items()
    ])


def register_socketio_events(socketio):
    pass
