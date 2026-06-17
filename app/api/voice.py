"""语音合成 (TTS) API — Microsoft Edge TTS（免费，CLI 模式）"""
import subprocess
import tempfile
import os
import base64
from flask import Blueprint, request
from app.utils.response import success, error

voice_bp = Blueprint('voice', __name__)

# 可用音色
VOICES = {
    "xiaoxiao": {"name": "zh-CN-XiaoxiaoNeural", "label": "晓晓 (女·温柔)"},
    "yunxi":   {"name": "zh-CN-YunxiNeural",   "label": "云希 (男·阳光)"},
    "xiaoyi":  {"name": "zh-CN-XiaoyiNeural",  "label": "晓伊 (女·活泼)"},
    "yunyang": {"name": "zh-CN-YunyangNeural", "label": "云扬 (男·沉稳)"},
    "xiaochen": {"name": "zh-CN-XiaochenNeural", "label": "晓辰 (女·温柔)"},
}


def _generate_tts_cli(text, voice="zh-CN-XiaoxiaoNeural", rate="+5%"):
    """使用 edge-tts CLI 生成语音，返回 MP3 字节"""
    # 写入临时文件
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix='.mp3')
        os.close(fd)

        result = subprocess.run(
            ["edge-tts", "--voice", voice, "--rate", rate,
             "--text", text, "--write-media", tmp_path],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"edge-tts failed: {result.stderr[:200]}")

        with open(tmp_path, 'rb') as f:
            return f.read()

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@voice_bp.route('/tts', methods=['POST'])
def tts():
    """
    文本转语音
    POST /api/v1/tts
    Body: {"text": "...", "voice": "xiaoxiao"}
    """
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    voice_key = data.get("voice", "xiaoxiao")
    rate = data.get("rate", "+5%")

    if not text:
        return error("text 参数不能为空", 400)
    if len(text) > 5000:
        return error("文本过长，请控制在 5000 字以内", 400)

    try:
        voice_name = VOICES.get(voice_key, VOICES["xiaoxiao"])["name"]
        audio_bytes = _generate_tts_cli(text, voice_name, rate)
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return success({
            "audio": audio_b64,
            "format": "mp3",
            "voice": voice_name,
            "text_length": len(text),
        })
    except subprocess.TimeoutExpired:
        return error("语音合成超时，请稍后重试", 500)
    except FileNotFoundError:
        return error("edge-tts 未安装，请运行: pip install edge-tts", 500)
    except Exception as e:
        return error(f"语音合成失败: {str(e)}", 500)


@voice_bp.route('/voices', methods=['GET'])
def list_voices():
    """获取可用音色列表"""
    return success([
        {"key": k, "label": v["label"]}
        for k, v in VOICES.items()
    ])


def register_socketio_events(socketio):
    """注册 SocketIO 事件（语音通过 HTTP 实现，SocketIO 备用）"""
    pass
