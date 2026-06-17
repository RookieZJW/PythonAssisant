# 🚀 部署文档

Python 多功能智能助手生产环境部署指南，涵盖 Gunicorn + Nginx、Docker、HTTPS 及运维监控。

---

## 📋 部署架构

```
Internet → Nginx (:80/:443) → Gunicorn + gevent (:8000) → Flask
                                  ↓
                            MySQL (:3306) + Redis (:6379)
```

| 组件 | 端口 | 作用 |
|------|------|------|
| Nginx | 80/443 | 反向代理、SSL、静态文件 |
| Gunicorn + gevent | 8000 | WSGI 多进程，SSE 支持 |
| MySQL 8.0 | 3306 | 数据存储 |
| Redis 7.0 | 6379 | 限流（可选） |

---

## 🖥️ 服务器要求

| 资源 | 最低 | 推荐 |
|------|------|------|
| CPU | 2 核 | 4 核+ |
| 内存 | 2 GB | 4 GB+ |
| 磁盘 | 10 GB | 20 GB SSD |
| 系统 | Ubuntu 20.04+ | Ubuntu 22.04 LTS |

---

## 方案一：Gunicorn + Nginx（推荐生产）

### 1. 环境准备

```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nginx mysql-server redis-server supervisor
sudo systemctl enable mysql redis-server nginx --now
```

### 2. 创建数据库

```sql
CREATE DATABASE smart_assistant CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'assistant'@'localhost' IDENTIFIED BY 'YourStrongPassword!';
GRANT ALL ON smart_assistant.* TO 'assistant'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 部署应用

```bash
sudo mkdir -p /opt/smart-assistant && sudo chown $USER:$USER /opt/smart-assistant
cd /opt/smart-assistant
# 复制项目文件到此目录

python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. 配置环境变量

```bash
# 生成强密钥
SECRET=$(openssl rand -hex 32)

cat > .env << EOF
FLASK_ENV=production
SECRET_KEY=$SECRET
DEEPSEEK_API_KEY=sk-your-key
DEFAULT_MODEL=deepseek
TEMPERATURE=0.7
MAX_TOKENS=2048
DATABASE_URL=mysql+pymysql://assistant:YourStrongPassword!@localhost:3306/smart_assistant
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT=60
EOF

chmod 600 .env
```

### 5. Supervisor 守护

```bash
sudo tee /etc/supervisor/conf.d/smart-assistant.conf << 'EOF'
[program:smart-assistant]
command=/opt/smart-assistant/venv/bin/gunicorn -c /opt/smart-assistant/gunicorn_config.py run:app
directory=/opt/smart-assistant
user=www-data
autostart=true
autorestart=true
stderr_logfile=/opt/smart-assistant/logs/supervisor_error.log
stdout_logfile=/opt/smart-assistant/logs/supervisor.log
EOF

sudo supervisorctl reread && sudo supervisorctl update
```

### 6. Nginx 配置

```nginx
# /etc/nginx/sites-available/smart-assistant
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    client_max_body_size 10M;
    gzip on;
    gzip_types application/json text/css application/javascript;

    location / {
        root /opt/smart-assistant/static;
        index index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 流式响应必须关闭缓冲
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
    }

    location /static/ {
        alias /opt/smart-assistant/static/;
        expires 30d;
    }
}
```

```bash
sudo ln -sf /etc/nginx/sites-available/smart-assistant /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

### 7. HTTPS 证书

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 方案二：Docker Compose

```bash
cd PythonAssistant
# 编辑 .env 填入配置
docker compose up -d --build
```

```yaml
# docker-compose.yml
services:
  app:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    environment: [FLASK_ENV=production]
    volumes: [./logs:/app/logs]
    depends_on: [redis]
    restart: unless-stopped
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: [redis_data:/data]
    restart: unless-stopped
volumes:
  redis_data:
```

外挂 Nginx 反向代理到 `localhost:8000`。

---

## 运维

### 日志

```bash
tail -f /opt/smart-assistant/logs/error.log    # 应用错误
tail -f /opt/smart-assistant/logs/access.log   # 请求日志
tail -f /var/log/nginx/error.log               # Nginx 错误
sudo supervisorctl tail -f smart-assistant     # 进程日志
docker logs -f smart-assistant                 # Docker 日志
```

### 数据库备份

```bash
# 每日凌晨 2 点备份
cat > /opt/smart-assistant/backup.sh << 'EOF'
#!/bin/bash
mkdir -p /opt/backups/mysql
DATE=$(date +%Y%m%d_%H%M%S)
mysqldump -u assistant -p'YourPassword' smart_assistant \
  --single-transaction | gzip > /opt/backups/mysql/assistant_$DATE.sql.gz
find /opt/backups/mysql -mtime +30 -delete
EOF

chmod +x /opt/smart-assistant/backup.sh
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/smart-assistant/backup.sh") | crontab -
```

### 健康检查

```bash
# 每 5 分钟检查
(crontab -l 2>/dev/null; echo "*/5 * * * * curl -sf http://localhost:8000/api/v1/health || echo '[FAIL]' >> /opt/smart-assistant/logs/health.log") | crontab -
```

### 更新

```bash
cd /opt/smart-assistant
git pull
source venv/bin/activate && pip install -r requirements.txt
sudo supervisorctl restart smart-assistant
```

---

## 故障排查

| 现象 | 可能原因 | 解决 |
|------|----------|------|
| 502 | Gunicorn 未启动 | `sudo supervisorctl restart smart-assistant` |
| 504 | 模型响应超时 | 加大 `proxy_read_timeout` 和 `timeout` |
| SSE 打字无效 | Nginx 缓冲 | `proxy_buffering off` |
| 数据库连接失败 | MySQL 密码错误或未运行 | 检查 `.env` 和服务状态 |
| 429 | 触发限流 | 调整 `RATE_LIMIT` |

---

## 安全检查清单

- [ ] `FLASK_ENV=production`，`DEBUG=False`
- [ ] `SECRET_KEY` 使用 `openssl rand -hex 32` 生成
- [ ] API Key 不在代码中，`.env` 权限 `600`
- [ ] MySQL 使用独立用户（非 root）
- [ ] 防火墙仅开放 22/80/443
- [ ] SSL 证书已配置
- [ ] `.gitignore` 包含 `.env`

---

## 性能调优

```python
# gunicorn_config.py
workers = cpu_count * 2 + 1
worker_class = "gevent"         # SSE 必须
worker_connections = 1000
timeout = 120
max_requests = 10000            # 防内存泄漏
max_requests_jitter = 1000
preload_app = True
```
