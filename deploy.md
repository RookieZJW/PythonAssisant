# 🚀 部署文档

本文档详细说明 **Python 多功能智能助手** 的生产环境部署方案，涵盖 **Gunicorn + Nginx** 传统部署、**Docker** 容器化部署、**HTTPS** 配置及运维监控。

---

## 📋 目录

- [部署架构](#部署架构)
- [环境要求](#环境要求)
- [方案一：Gunicorn + Nginx（推荐生产）](#方案一gunicorn--nginx推荐生产)
- [方案二：Docker Compose（快速部署）](#方案二docker-compose快速部署)
- [方案三：Docker + Nginx 组合](#方案三docker--nginx-组合)
- [HTTPS 配置](#https-配置)
- [生产环境检查清单](#生产环境检查清单)
- [运维与监控](#运维与监控)
- [故障排查](#故障排查)
- [性能调优](#性能调优)

---

## 部署架构

```
                    Internet
                       │
                ┌──────▼──────┐
                │   Nginx     │  ← 反向代理 + 静态文件 + SSL 终端
                │  :80/:443   │
                └──────┬──────┘
                       │
           ┌───────────┼───────────┐
           │           │           │
    ┌──────▼──┐ ┌──────▼──┐ ┌──────▼──┐
    │Gunicorn │ │Gunicorn │ │Gunicorn │  ← WSGI 多 Worker
    │Worker 1 │ │Worker 2 │ │Worker N │
    └────┬────┘ └────┬────┘ └────┬────┘
         │           │           │
         └───────────┼───────────┘
                     │
          ┌──────────┼──────────┐
          │          │          │
    ┌─────▼───┐ ┌───▼────┐ ┌───▼──────┐
    │  MySQL  │ │ Redis  │ │ LLM API  │  ← 外部服务
    │ :3306   │ │ :6379  │ │ (外网)    │
    └─────────┘ └────────┘ └──────────┘
```

### 组件说明

| 组件 | 端口 | 作用 |
|------|------|------|
| **Nginx** | 80 / 443 | 反向代理、SSL 终止、静态文件、限流 |
| **Gunicorn** | 8000 (内部) | WSGI 服务器，多进程处理请求 |
| **gevent** | - | 异步 Worker，支持 SSE 长连接 |
| **MySQL** | 3306 | 会话/消息/用户数据持久化 |
| **Redis** | 6379 | 限流计数器 |

---

## 环境要求

### 服务器最低配置

| 资源 | 最低 | 推荐 |
|------|------|------|
| **CPU** | 2 核 | 4 核+ |
| **内存** | 2 GB | 4 GB+ |
| **磁盘** | 10 GB | 20 GB SSD |
| **系统** | Ubuntu 20.04+ / CentOS 7+ / Windows Server | Ubuntu 22.04 LTS |
| **网络** | 可访问 DeepSeek API (api.deepseek.com) | - |

### 依赖软件

| 软件 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 应用运行时 |
| MySQL | 8.0+ | 数据存储 |
| Redis | 7.0+ | 限流（可选） |
| Nginx | 1.20+ | 反向代理 |
| Git | 2.x+ | 版本管理（可选） |

---

## 方案一：Gunicorn + Nginx（推荐生产）

### 1. 环境准备（Ubuntu 示例）

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础依赖
sudo apt install -y python3 python3-pip python3-venv \
    nginx mysql-server redis-server supervisor

# 启动服务
sudo systemctl enable mysql redis-server nginx
sudo systemctl start mysql redis-server
```

### 2. 创建 MySQL 数据库

```sql
-- 登录 MySQL
sudo mysql -u root

-- 创建数据库
CREATE DATABASE smart_assistant
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 创建用户（替换密码）
CREATE USER 'assistant'@'localhost' IDENTIFIED BY 'YourSecurePassword123!';
GRANT ALL PRIVILEGES ON smart_assistant.* TO 'assistant'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 3. 部署应用代码

```bash
# 创建部署目录
sudo mkdir -p /opt/smart-assistant
sudo chown $USER:$USER /opt/smart-assistant

# 复制项目文件
cd /opt/smart-assistant
# 将项目文件复制到此目录

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
# 国内镜像加速：
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. 配置环境变量

```bash
# 创建 .env 文件
cat > /opt/smart-assistant/.env << 'EOF'
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)

# 模型配置
DEFAULT_MODEL=deepseek
TEMPERATURE=0.7
MAX_TOKENS=2048

# API Keys
DEEPSEEK_API_KEY=sk-your-deepseek-key
DEEPSEEK_MODEL=deepseek-chat
QWEN_API_KEY=sk-your-qwen-key
QWEN_MODEL=qwen-plus

# 数据库
DATABASE_URL=mysql+pymysql://assistant:YourSecurePassword123!@localhost:3306/smart_assistant

# Redis
REDIS_URL=redis://localhost:6379/0

# 限流
RATE_LIMIT=60

# CORS（生产环境配置允许的域名）
# CORS_ORIGINS=["https://your-domain.com"]
EOF
```

> ⚠️ 使用 `openssl rand -hex 32` 生成强随机 SECRET_KEY

### 5. 配置 Gunicorn

项目已包含 `gunicorn_config.py`，按需调整：

```python
# gunicorn_config.py
bind = "127.0.0.1:8000"          # 只监听本地，通过 Nginx 暴露
workers = 5                       # CPU * 2 + 1
worker_class = "gevent"           # 支持 SSE 流式响应
worker_connections = 1000
timeout = 120
keepalive = 5
loglevel = "warning"
accesslog = "logs/access.log"
errorlog = "logs/error.log"
```

手动启动测试：

```bash
cd /opt/smart-assistant
source venv/bin/activate
gunicorn -c gunicorn_config.py run:app

# 测试
curl http://127.0.0.1:8000/api/v1/health
```

### 6. 配置 Supervisor（进程守护）

```bash
sudo cat > /etc/supervisor/conf.d/smart-assistant.conf << 'EOF'
[program:smart-assistant]
command=/opt/smart-assistant/venv/bin/gunicorn -c /opt/smart-assistant/gunicorn_config.py run:app
directory=/opt/smart-assistant
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/smart-assistant/logs/supervisor.log
environment=PATH="/opt/smart-assistant/venv/bin"

[group:smart-assistant-group]
programs=smart-assistant
EOF

# 重载配置并启动
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl status smart-assistant
```

### 7. 配置 Nginx

```bash
sudo cat > /etc/nginx/sites-available/smart-assistant << 'NGINX'
# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name your-domain.com;

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书
    ssl_certificate     /etc/ssl/certs/your-domain.pem;
    ssl_certificate_key /etc/ssl/private/your-domain.key;

    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers on;

    # 上传大小限制
    client_max_body_size 10M;

    # Gzip 压缩
    gzip on;
    gzip_types application/json text/plain text/css application/javascript;

    # 静态文件（Web 聊天界面）
    location / {
        root /opt/smart-assistant/static;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理到 Gunicorn
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 流式响应支持（关键！）
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
    }

    # 健康检查不需要缓冲
    location /api/v1/health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_buffering off;
    }
}
NGINX

# 启用站点
sudo ln -sf /etc/nginx/sites-available/smart-assistant /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

> ⚠️ **SSE 流式响应关键配置**：`proxy_buffering off` 和 `proxy_read_timeout 300s` 必须设置，否则流式输出会被缓冲，用户体验极差。

### 8. 防火墙配置

```bash
# UFW 防火墙
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable

# 或 firewalld
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 9. 验证部署

```bash
# 本地检查
curl http://127.0.0.1:8000/api/v1/health

# 通过 Nginx 检查
curl https://your-domain.com/api/v1/health

# 检查 Supervisor 状态
sudo supervisorctl status

# 检查 Nginx 状态
sudo systemctl status nginx

# 查看日志
tail -f /opt/smart-assistant/logs/access.log
tail -f /opt/smart-assistant/logs/error.log
```

---

## 方案二：Docker Compose（快速部署）

### 1. 安装 Docker

```bash
# Ubuntu
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# 安装 Docker Compose
sudo apt install docker-compose-plugin
```

### 2. 准备配置文件

确认项目目录下有 `Dockerfile`、`docker-compose.yml` 和 `.env`。

### 3. 启动

```bash
cd /opt/smart-assistant

# 构建并启动
docker compose up -d --build

# 查看状态
docker compose ps
docker compose logs -f app
```

### 4. docker-compose.yml 说明

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"          # 映射到宿主机
    environment:
      - FLASK_ENV=production
    env_file:
      - .env                 # 从 .env 加载所有变量
    volumes:
      - ./logs:/app/logs     # 日志持久化
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

### 5. 搭配 Nginx

Docker 只跑应用，Nginx 仍装在宿主机，反向代理到 `localhost:8000`（配置同方案一 Nginx 部分）。

---

## 方案三：Docker + Nginx 组合

适合已有 Nginx 的服务器，只把应用容器化。

### Dockerfile（已提供）

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p logs

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn_config.py", "run:app"]
```

### 构建并运行

```bash
# 构建镜像
docker build -t smart-assistant:latest .

# 运行容器
docker run -d \
  --name smart-assistant \
  --restart unless-stopped \
  -p 127.0.0.1:8000:8000 \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  smart-assistant:latest

# 查看日志
docker logs -f smart-assistant
```

外层的 Nginx 配置同方案一。

---

## HTTPS 配置

### Let's Encrypt 免费证书（推荐）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书并自动配置 Nginx
sudo certbot --nginx -d your-domain.com

# 自动续期（已内置 timer）
sudo certbot renew --dry-run
```

### 手动 HTTPS Nginx 配置

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # ... 其余配置同方案一
}
```

---

## 生产环境检查清单

部署前逐项确认：

### 安全

- [ ] `FLASK_ENV=production`
- [ ] `SECRET_KEY` 使用 `openssl rand -hex 32` 生成
- [ ] `DEBUG=False`（生产配置已默认）
- [ ] API Key 不在代码中硬编码，使用 `.env`
- [ ] `.env` 文件权限 `600`：`chmod 600 .env`
- [ ] MySQL 使用独立用户（非 root）
- [ ] MySQL 密码强度足够（12 字符+，含大小写+数字+符号）
- [ ] CORS `origins` 限定为实际域名
- [ ] 防火墙仅开放 22、80、443 端口
- [ ] SSL 证书已配置且有效

### 性能

- [ ] Gunicorn worker 数量 = CPU 核心数 × 2 + 1
- [ ] `worker_class = "gevent"` 确保 SSE 流式响应正常
- [ ] MySQL 连接池 `pool_size` 合理（默认 10）
- [ ] Nginx `proxy_buffering off`（SSE 必须）
- [ ] Nginx Gzip 压缩开启
- [ ] Redis 连接正常（如使用限流）

### 可靠性

- [ ] Supervisor 或 systemd 守护进程已配置
- [ ] `autorestart=true`（进程崩溃自动重启）
- [ ] Docker 容器 `restart: unless-stopped`
- [ ] MySQL 数据定期备份（见运维章节）
- [ ] 日志轮转已配置（`logrotate`）
- [ ] 磁盘空间监控告警

### 功能验证

```bash
# 1. 健康检查
curl https://your-domain.com/api/v1/health

# 2. 对话测试
curl -X POST https://your-domain.com/api/v1/chat \
  -H "Content-Type: application/json" \
  --data-raw '{"message":"Hello"}'

# 3. 流式对话测试
curl -N -X POST https://your-domain.com/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  --data-raw '{"message":"Count from 1 to 5"}'

# 4. 会话管理测试
curl https://your-domain.com/api/v1/conversations

# 5. Web 界面访问
curl -I https://your-domain.com/
```

---

## 运维与监控

### 日志管理

```bash
# 应用日志
tail -f /opt/smart-assistant/logs/access.log
tail -f /opt/smart-assistant/logs/error.log

# Gunicorn 日志（Supervisor 管理的）
sudo supervisorctl tail -f smart-assistant

# Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Docker 日志
docker logs -f smart-assistant
```

### Logrotate 日志轮转

```bash
sudo cat > /etc/logrotate.d/smart-assistant << 'EOF'
/opt/smart-assistant/logs/*.log {
    daily
    rotate 30
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
    dateext
}
EOF
```

### 数据库备份

```bash
# 创建备份脚本
cat > /opt/smart-assistant/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/mysql"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
mysqldump -u assistant -p'YourPassword' smart_assistant \
  --single-transaction --routines --triggers \
  | gzip > "$BACKUP_DIR/smart_assistant_$DATE.sql.gz"

# 只保留最近 30 天
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
EOF

chmod +x /opt/smart-assistant/backup.sh

# 添加定时任务（每天凌晨 2 点）
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/smart-assistant/backup.sh") | crontab -
```

### 健康监控

```bash
# 添加 cron 健康检查
cat > /opt/smart-assistant/health_check.sh << 'EOF'
#!/bin/bash
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health)

if [ "$RESPONSE" != "200" ]; then
    echo "[$(date)] Health check FAILED (HTTP $RESPONSE)" >> /opt/smart-assistant/logs/health_check.log
    # 可选：发送告警通知
fi
EOF

# 每 5 分钟检查一次
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/smart-assistant/health_check.sh") | crontab -
```

### 性能监控

```bash
# 查看进程状态
sudo supervisorctl status

# 查看资源占用
htop -p $(pgrep -f gunicorn | paste -sd,)

# MySQL 连接数
mysql -u assistant -p -e "SHOW PROCESSLIST;"

# Redis 内存
redis-cli INFO memory | grep used_memory_human
```

---

## 故障排查

### 问题对照表

| 现象 | 可能原因 | 解决方法 |
|------|----------|----------|
| **502 Bad Gateway** | Gunicorn 未启动 | `sudo supervisorctl restart smart-assistant` |
| **504 Gateway Timeout** | 模型响应超时 | 增加 `proxy_read_timeout` 和 `timeout` |
| **流式响应变成一次性返回** | Nginx 开启了缓冲 | 设置 `proxy_buffering off` |
| **CORS 错误** | Origins 配置不匹配 | 检查 `CORS_ORIGINS` 是否包含实际域名 |
| **数据库连接失败** | MySQL 未运行或密码错误 | 检查服务状态和 `.env` |
| **429 Too Many Requests** | 触发限流 | 调整 `RATE_LIMIT` 或检查 Redis |
| **Web 页面空白** | 静态文件路径错误 | 确认 Nginx `root` 指向正确目录 |
| **Worker 频繁重启** | 内存不足 | 减少 worker 数或增加服务器内存 |

### 调试命令

```bash
# 前台运行 Gunicorn 查看错误
cd /opt/smart-assistant
source venv/bin/activate
gunicorn -c gunicorn_config.py run:app --log-level debug

# 手动启动 Flask 开发服务器测试
FLASK_ENV=development python run.py

# 测试数据库连接
python -c "
from sqlalchemy import create_engine
engine = create_engine('mysql+pymysql://assistant:pass@localhost:3306/smart_assistant')
conn = engine.connect()
print('DB OK')
conn.close()
"

# 测试 Redis 连接
redis-cli ping

# 检查端口占用
sudo netstat -tlnp | grep -E "80|443|8000|3306|6379"

# Nginx 配置测试
sudo nginx -t

# 查看系统资源
free -h
df -h
uptime
```

---

## 性能调优

### Gunicorn

```python
# 根据服务器配置调整
workers = multiprocessing.cpu_count() * 2 + 1   # Worker 数量
worker_class = "gevent"                           # SSE 必须
worker_connections = 1000                         # 每 Worker 连接数
timeout = 120                                     # 请求超时
max_requests = 10000                              # Worker 处理请求数后自动重启（防内存泄漏）
max_requests_jitter = 1000                        # 随机抖动避免同时重启
preload_app = True                                # 预加载应用（减少内存）
```

### MySQL

```sql
-- 增加连接数
SET GLOBAL max_connections = 200;

-- 查看慢查询
SHOW VARIABLES LIKE 'slow_query_log';
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 2;
```

```ini
# my.cnf 推荐配置
[mysqld]
max_connections = 200
innodb_buffer_pool_size = 512M
innodb_log_file_size = 256M
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
```

### Nginx

```nginx
# nginx.conf 工作进程
worker_processes auto;
worker_connections 2048;

# 静态文件缓存
location /static/ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# API 连接数限制
limit_conn_zone $binary_remote_addr zone=api:10m;
limit_conn api 20;
```

---

## 更新部署

```bash
# 1. 拉取最新代码
cd /opt/smart-assistant
git pull origin main  # 或手动替换文件

# 2. 更新依赖
source venv/bin/activate
pip install -r requirements.txt

# 3. 重启服务
sudo supervisorctl restart smart-assistant

# Docker 方式
docker compose down
docker compose up -d --build
```

---

## 安全加固建议

1. **API Key 管理**：定期轮换 API Key，不要提交到 Git
2. **数据库隔离**：应用使用独立 MySQL 用户，限制权限
3. **访问控制**：生产环境启用 API Key 认证中间件
4. **请求限流**：根据业务量调整 `RATE_LIMIT`（默认 60次/分钟）
5. **日志脱敏**：不要在日志中打印 API Key 或用户敏感信息
6. **定期更新**：及时更新 Python 包，修复安全漏洞
7. **网络隔离**：MySQL 和 Redis 只监听 localhost
