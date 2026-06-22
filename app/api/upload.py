"""
文件上传与解析模块 API 路由
=============================
提供文件上传、解析和附件管理功能，包括：
- 上传文件并解析文本内容（支持 TXT、PDF、Word、代码文件等）
- 获取会话的当前附件信息
- 移除会话的附件

文件上传后会解析为纯文本，然后立即从磁盘删除（不留存文件），
解析后的内容存储在内存字典中供对话接口使用。
"""
import os
from flask import Blueprint, request
from werkzeug.utils import secure_filename
from app.utils.response import success, error

# 创建名为 'upload' 的蓝图，用于组织文件上传相关的路由
upload_bp = Blueprint('upload', __name__)

# 上传文件的临时存储目录（相对于项目根目录的 uploads/ 文件夹）
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads')

# 允许上传的文件扩展名集合
# 涵盖常见文本文档、代码文件和纯文本格式
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc', 'md', 'py', 'js', 'html', 'css', 'json', 'xml', 'csv', 'log', 'java', 'c', 'cpp', 'h'}

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 存储会话附件的内存字典
# 结构: {conversation_id: {filename, content, size, type}}
# 注意: 附件内容仅在应用运行期间保存在内存中，重启后清空
session_files = {}


def _allowed_file(filename):
    """
    检查文件扩展名是否在允许列表中
    ---------------------------------
    参数:
        filename: 文件名（含扩展名）
    返回:
        True 如果文件类型被允许，否则 False
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _parse_file(filepath, filename):
    """
    解析文件内容为纯文本
    ------------------------
    根据文件扩展名选择合适的解析器：
    - 纯文本/代码文件: 直接 UTF-8 读取
    - PDF: 使用 PyPDF2 提取文字（最多 20 页）
    - Word 文档: 使用 python-docx 提取段落文字
    - 其他格式: 返回不支持提示

    参数:
        filepath: 文件的完整磁盘路径
        filename: 原始文件名（用于判断扩展名）

    返回:
        解析后的文本内容字符串
    """
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    # ---- 纯文本/代码文件：直接读取 ----
    if ext == 'txt' or ext in ('md', 'py', 'js', 'html', 'css', 'json', 'xml', 'csv', 'log', 'java', 'c', 'cpp', 'h'):
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

    # ---- PDF 文件：使用 PyPDF2 解析 ----
    if ext == 'pdf':
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(filepath)
            text = []
            # 限制最多解析 20 页，避免处理超大型 PDF
            for page in reader.pages[:20]:
                t = page.extract_text()
                if t:
                    text.append(t)
            return '\n\n'.join(text)
        except ImportError:
            return "[错误] 未安装 PyPDF2，无法解析 PDF。请运行 pip install PyPDF2"

    # ---- Word 文档：使用 python-docx 解析 ----
    if ext in ('docx', 'doc'):
        try:
            from docx import Document
            doc = Document(filepath)
            # 提取所有非空段落文本
            return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            return "[错误] 未安装 python-docx，无法解析 Word。请运行 pip install python-docx"

    # ---- 不支持的格式 ----
    return f"[不支持的文件格式] {ext}"


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    上传文件并解析内容
    --------------------
    接收前端上传的文件，执行以下流程：
    1. 校验文件是否存在及格式是否允许
    2. 保存到临时目录（使用安全文件名）
    3. 解析文件内容为纯文本
    4. 限制内容长度不超过 8000 字符
    5. 将解析结果存入内存字典，供对话接口引用
    6. 从磁盘删除临时文件（不留存）

    请求体 (multipart/form-data):
        - file (必填): 要上传的文件
        - conversation_id (可选): 关联的会话 ID

    返回:
        JSON 响应，包含文件名、大小、内容和预览
    """
    # 检查请求中是否包含文件
    if 'file' not in request.files:
        return error("请选择文件", 400)

    file = request.files['file']
    conv_id = request.form.get('conversation_id', '')

    # 检查文件名是否为空
    if file.filename == '':
        return error("文件名为空", 400)
    # 检查文件类型是否允许
    if not _allowed_file(file.filename):
        return error(f"不支持的文件格式。支持: {', '.join(sorted(ALLOWED_EXTENSIONS))}", 400)

    # 使用 Werkzeug 的安全文件名处理，防止路径穿越攻击
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        # 保存上传的文件到临时目录
        file.save(filepath)
        # 立即关闭文件句柄，释放系统资源
        file.close()

        # 解析文件内容
        content = _parse_file(filepath, filename)
        size = os.path.getsize(filepath)

        # 限制内容长度，避免超出 LLM 上下文窗口
        if len(content) > 8000:
            content = content[:8000] + "\n\n...(内容过长，已截断前8000字符)"

        # 将解析结果存入内存字典
        session_files[conv_id] = {
            'filename': filename,
            'content': content,
            'size': size,
            'type': filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        }

        # 返回解析结果给前端
        return success({
            'filename': filename,
            'size': size,
            'content': content,
            'preview': content[:300] + ('...' if len(content) > 300 else ''),
        })
    except Exception as e:
        # 解析过程中发生异常
        return error(f"文件解析失败: {str(e)}", 500)
    finally:
        # 无论成功还是失败，都删除临时文件
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass


@upload_bp.route('/upload/<conv_id>', methods=['GET'])
def get_attachment(conv_id):
    """
    获取会话当前附件信息
    -----------------------
    根据会话 ID 查询内存中存储的附件信息。

    路径参数:
        - conv_id: 会话 ID

    返回:
        JSON 响应，包含附件信息（文件名、内容、大小等）；
        若无附件则返回 null
    """
    info = session_files.get(conv_id)
    if not info:
        return success(None)
    return success(info)


@upload_bp.route('/upload/<conv_id>', methods=['DELETE'])
def remove_attachment(conv_id):
    """
    移除会话的附件
    -----------------
    从内存字典中删除指定会话的附件数据。

    路径参数:
        - conv_id: 会话 ID

    返回:
        JSON 响应，表示移除成功
    """
    session_files.pop(conv_id, None)
    return success(None, "附件已移除")
