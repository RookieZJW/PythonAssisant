FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 安装依赖（requirements.txt 与本机开发环境同源，pip freeze 生成）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY . .

# 创建运行时目录（日志 / 上传临时文件）
RUN mkdir -p logs uploads

# 暴露端口（Gunicorn 默认 8000，可用 PORT 环境变量覆盖）
EXPOSE 8000

# 启动命令（配置见 gunicorn_config.py，gevent worker 支持 SSE 流式响应）
# 注意：语音对话的 WebSocket 在 Gunicorn 下会自动退化为长轮询；
# 如需完整 WebSocket，请用 python run.py（开发/Werkzeug）或接入 Nginx 透传 Upgrade
CMD ["gunicorn", "-c", "gunicorn_config.py", "run:app"]
