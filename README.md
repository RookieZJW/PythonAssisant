# 🤖 Python 多功能智能助手 v2.6

基于 **Flask + LangChain** 的全栈 AI 对话系统。支持**用户登录注册**、**SSE 流式 Markdown**、**双引擎 TTS**、**12 套主题**、**角色绑定**、**文件附件**。

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green)](https://flask.palletsprojects.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-orange)](https://langchain.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-utf8mb4-blue)](https://mysql.com)

---

## ✨ 功能

| 分类 | 功能 |
|------|------|
| 🔐 登录系统 | 用户名密码注册/登录，Session 认证，数据隔离 |
| 📱 预留登录 | 手机验证码、微信/QQ扫码（UI就绪，需企业资质） |
| 🤖 双模型 | DeepSeek + 通义千问，策略模式一键切换 |
| ⚡ 流式 SSE | Token 级实时输出，JSON-SSE 换行保护 |
| 📝 Markdown | 流式实时渲染，代码高亮+复制 |
| 🎤 语音 | 浏览器 STT + 火山/腾讯 TTS（11音色） |
| 🎭 角色 | 6内置+自定义，对话绑定，用户隔离 |
| 🎨 主题 | 12套预设，透明度/阴影/边框可调，背景图/视频 |
| 📎 附件 | PDF/Word/TXT上传，AI基于内容回答 |
| ⚙️ 参数 | Temperature/MaxTokens/Top-P 面板 |
| 📊 统计 | 每条消息Token + 今日累计 |
| 📥 导出 | 对话导出Markdown文件 |
| 🗑️ 管理 | 硬删除，会话改名 |

---

## 🚀 快速开始

```bash
pip install -r requirements.txt
# 编辑 .env 填入 DEEPSEEK_API_KEY
python run.py
# → 浏览器打开 http://localhost:5000/login 注册登录
```

详细使用说明见 **[使用指南.md](docs/使用指南.md)**

---

## ⚙️ 配置 (.env)

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key（必填） |
| `QWEN_API_KEY` | 通义千问（可选） |
| `VOLCANO_TTS_APP_ID/TOKEN` | 火山TTS（可选） |
| `TENCENT_TTS_SECRET_ID/KEY` | 腾讯TTS（可选） |
| `DATABASE_URL` | MySQL 连接串 |
| `REDIS_URL` | Redis（可选，无限流也不影响使用） |
| `FLASK_ENV` | development / production / testing |

---

## 📡 API (25+)

| 蓝图 | 方法 | 路径 | 说明 |
|------|------|------|------|
| auth | POST | /auth/register | 注册 |
| auth | POST | /auth/login | 登录 |
| auth | GET/POST | /auth/me, /auth/logout | 用户信息/退出 |
| chat | POST | /chat, /chat/stream | 对话/流式 |
| conversation | CRUD | /conversations/{id} | 会话管理+改名 |
| conversation | GET | /conversations/{id}/export | 导出Markdown |
| role | CRUD | /roles/{id} | 角色管理(同名检测) |
| voice | POST | /tts | TTS(火山/腾讯) |
| system | GET | /health, /models, /stats | 系统 |
| upload | POST | /upload | 文件上传 |
| backgrounds | GET/POST/DELETE | /backgrounds/{id} | 背景历史 |

---

## 📁 项目结构

```
PythonAssistant/
├── run.py                     # 启动入口
├── requirements.txt           # 依赖
├── .env / .env.example        # 配置
├── Dockerfile / compose.yml   # Docker
├── gunicorn_config.py         # 生产WSGI
├── app/
│   ├── __init__.py            # 工厂+登录保护
│   ├── config/                # settings, prompts
│   ├── models/                # user, role, conversation, message, background
│   ├── llm/                   # 策略模式 (DeepSeek/Qwen)
│   ├── services/              # chat, model, tool
│   ├── api/                   # auth, chat, conversation, role, voice, system, upload, background_api
│   ├── tools/                 # calculator, analyzer, search
│   ├── middleware/            # auth, rate_limit, logger
│   └── utils/                 # response, exceptions, validators
├── static/                    # index.html, login.html, mic-test.html, resume.html, ppt.html
├── docs/                      # README, deploy, 使用指南, 生产实习报告, database_schema.sql
└── tests/
```

---

## 📚 文档

| 文档 | 内容 |
|------|------|
| [使用指南.md](docs/使用指南.md) | 安装、配置、日常使用教程 |
| [deploy.md](deploy.md) | Gunicorn+Nginx+Docker 生产部署 |
| [零基础入门指南.md](零基础入门指南.md) | 从零学编程，理解项目 |
| [database_schema.sql](docs/database_schema.sql) | MySQL 数据库结构 |
| [生产实习报告.md](docs/生产实习报告.md) | 实习报告 |

---

## 📄 License

MIT
