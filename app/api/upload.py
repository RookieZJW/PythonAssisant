"""文件上传 & 解析 API"""
import os
from flask import Blueprint, request
from werkzeug.utils import secure_filename
from app.utils.response import success, error

upload_bp = Blueprint('upload', __name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc', 'md', 'py', 'js', 'html', 'css', 'json', 'xml', 'csv', 'log', 'java', 'c', 'cpp', 'h'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 存储会话附件的字典 {conversation_id: {filename, content}}
session_files = {}


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _parse_file(filepath, filename):
    """解析文件内容"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    if ext == 'txt' or ext in ('md', 'py', 'js', 'html', 'css', 'json', 'xml', 'csv', 'log', 'java', 'c', 'cpp', 'h'):
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

    if ext == 'pdf':
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(filepath)
            text = []
            for page in reader.pages[:20]:  # 最多20页
                t = page.extract_text()
                if t: text.append(t)
            return '\n\n'.join(text)
        except ImportError:
            return "[错误] 未安装 PyPDF2，无法解析 PDF。请运行 pip install PyPDF2"

    if ext in ('docx', 'doc'):
        try:
            from docx import Document
            doc = Document(filepath)
            return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            return "[错误] 未安装 python-docx，无法解析 Word。请运行 pip install python-docx"

    return f"[不支持的文件格式] {ext}"


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """上传文件并解析内容"""
    if 'file' not in request.files:
        return error("请选择文件", 400)

    file = request.files['file']
    conv_id = request.form.get('conversation_id', '')

    if file.filename == '':
        return error("文件名为空", 400)
    if not _allowed_file(file.filename):
        return error(f"不支持的文件格式。支持: {', '.join(sorted(ALLOWED_EXTENSIONS))}", 400)

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        file.save(filepath)
        # 立即关闭文件句柄
        file.close()

        content = _parse_file(filepath, filename)
        size = os.path.getsize(filepath)

        if len(content) > 8000:
            content = content[:8000] + "\n\n...(内容过长，已截断前8000字符)"

        session_files[conv_id] = {
            'filename': filename,
            'content': content,
            'size': size,
            'type': filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        }

        return success({
            'filename': filename,
            'size': size,
            'content': content,
            'preview': content[:300] + ('...' if len(content) > 300 else ''),
        })
    except Exception as e:
        return error(f"文件解析失败: {str(e)}", 500)
    finally:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass


@upload_bp.route('/upload/<conv_id>', methods=['GET'])
def get_attachment(conv_id):
    """获取会话当前附件信息"""
    info = session_files.get(conv_id)
    if not info:
        return success(None)
    return success(info)


@upload_bp.route('/upload/<conv_id>', methods=['DELETE'])
def remove_attachment(conv_id):
    """移除附件"""
    session_files.pop(conv_id, None)
    return success(None, "附件已移除")
