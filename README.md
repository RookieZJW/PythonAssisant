# 🤖 Python 多功能智能助手

基于 **Flask + LangChain** 构建的多模型智能对话系统。支持 **语音对话 (STT + TTS)**、**SSE 流式响应**、**多角色系统**、**自定义角色**、**对话-角色绑定**、**工具调用**，自带科技感粒子动画 Web 界面。

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green)](https://flask.palletsprojects.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-orange)](https://langchain.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-blue)](https://mysql.com)
[![Redis](https://img.shields.io/badge/Redis-7.0-red)](https://redis.io)

---

## 📋 目录

- [功能特性](#-功能特性)
- [技术栈](#-技术栈)
- [项目结构](#-项目结构)
- [系统架构](#-系统架构)
- [快速开始](#-快速开始)
- [配置说明](#-配置说明)
- [API 文档](#-api-文档)
- [语音功能](#-语音功能)
- [角色系统](#-角色系统)
- [扩展开发](#-扩展开发)
- [常见问题](#-常见问题)
- [部署文档](#-部署文档)

---

## ✨ 功能特性

| 分类 | 功能 | 说明 |
|------|------|------|
| 🎤 **语音对话** | STT 语音输入 + TTS 语音输出 | 浏览器语音识别，Microsoft Edge TTS（5种音色） |
| 🎭 **多角色系统** | 6 内置角色 + 无限自定义 | 角色-对话绑定，切换对话自动恢复角色 |
| 💬 **对话管理** | 历史持久化 + 角色绑定 | 每条对话独立绑定角色，互不串扰 |
| 🤖 **多模型支持** | DeepSeek / 通义千问 | 统一接口，一键切换 |
| ⚡ **流式响应** | SSE Token 级实时输出 | 打字机效果 |
| 🧠 **对话记忆** | 滑动窗口 + MySQL 持久化 | 多轮上下文记忆 |
| 🔧 **工具调用** | 计算器 / 数据分析 / 网络搜索 | 可扩展插件系统 |
| 🎨 **科技感 UI** | 粒子背景 / 霓虹光效 | 深色科技风 |
| 🔐 **安全防护** | API Key 认证 / Redis 限流 | 生产级安全 |
| 🐳 **容器部署** | Docker / Docker Compose | 一键部署 |

---

## 🛠 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **Web 框架** | Flask 3.x + Flask-SocketIO | HTTP + WebSocket |
| **LLM** | LangChain 1.x | 模型编排、Prompt 管理 |
| **大模型** | DeepSeek / 通义千问 (DashScope) | 对话引擎 |
| **语音识别** | Web Speech API (浏览器内置) | STT，免费 |
| **语音合成** | edge-tts (Microsoft Edge TTS) | TTS，免费，5种自然音色 |
| **数据库** | MySQL 8.0 + SQLAlchemy 2.x | 会话/消息/用户/角色 |
| **缓存** | Redis 7.0 | 限流计数器 |
| **前端** | 原生 HTML/CSS/JS | 零依赖 SPA |
| **部署** | Gunicorn + gevent + Nginx | 生产 WSGI |

---

## 📁 项目结构

```
smart-assistant/
├── run.py                        # 🚀 启动入口 (SocketIO)
├── gunicorn_config.py            # ⚙️ Gunicorn 生产配置
├── requirements.txt              # 📦 Python 依赖
├── .env / .env.example           # 🔐 环境变量
├── Dockerfile                    # 🐳 Docker 镜像
├── docker-compose.yml            # 🐳 Docker 编排
├── README.md                     # 📖 项目文档
├── deploy.md                     # 🚀 部署文档
│
├── app/
│   ├── __init__.py               #   应用工厂 + 内置角色初始化
│   ├── extensions.py             #   Flask 扩展 (DB + SocketIO)
│   │
│   ├── config/
│   │   ├── settings.py           #   三环境配置
│   │   └── prompts.py            #   Prompt 模板
│   │
│   ├── models/                   # 🗄️ 数据模型（4 表）
│   │   ├── role.py               #   角色（内置 + 自定义）
│   │   ├── conversation.py       #   会话（绑定 role_id）
│   │   ├── message.py            #   消息
│   │   └── user.py               #   用户
│   │
│   ├── llm/                      # 🧠 大模型调用层 (策略模式)
│   │   ├── base.py               #   抽象基类
│   │   ├── deepseek_client.py    #   DeepSeek
│   │   ├── qwen_client.py        #   通义千问
│   │   └── memory.py             #   滑动窗口记忆
│   │
│   ├── services/                 # 💼 业务逻辑
│   │   ├── chat_service.py       #   对话流程
│   │   ├── model_service.py      #   模型工厂
│   │   └── tool_service.py       #   工具管理
│   │
│   ├── tools/                    # 🔧 工具插件
│   │   ├── calculator.py         #   数学计算
│   │   ├── data_analyzer.py      #   数据分析
│   │   └── web_search.py         #   网络搜索
│   │
│   ├── api/                      # 🌐 API 路由 (5 蓝图)
│   │   ├── chat.py               #   /chat, /chat/stream
│   │   ├── conversation.py       #   /conversations CRUD
│   │   ├── role.py               #   /roles CRUD
│   │   ├── voice.py              #   /tts, /voices
│   │   └── system.py             #   /health, /models, /tools
│   │
│   ├── middleware/               # 🛡️ 中间件
│   │   ├── auth.py               #   API Key 认证
│   │   ├── rate_limit.py         #   Redis 限流
│   │   └── logger.py             #   请求日志
│   │
│   └── utils/                    # 🧰 工具函数
│       ├── response.py           #   统一响应
│       ├── exceptions.py         #   全局错误处理
│       └── validators.py         #   参数校验
│
├── static/                       # 🌐 前端
│   ├── index.html                #   聊天界面 (语音+粒子动画)
│   └── mic-test.html             #   麦克风测试工具
│
├── tests/                        # 🧪 测试
│   ├── conftest.py
│   ├── test_chat.py
│   └── test_models.py
│
├── logs/                         # 📝 日志
└── migrations/                   # 🔄 数据库迁移
```

---

## 🏗 系统架构

```
  浏览器 (语音 STT + 粒子 UI)
       │
       ├── HTTP/SSE ──────┐
       ├── WebSocket ─────┤
       │                  ▼
       │          ┌──────────────┐
       │          │  Flask +      │
       │          │  SocketIO     │
       │          └──────┬───────┘
       │                 │
       │    ┌────────────┼────────────┐
       │    │            │            │
       │    ▼            ▼            ▼
       │  API 路由   业务服务      LLM 层
       │  (5蓝图)   (3Service)   (2 Client)
       │    │            │            │
       │    └────────────┼────────────┘
       │                 │
       ▼                 ▼
  Web Speech API    ┌────┴────┐
  (浏览器内置 STT)   │  MySQL  │  Redis
                    │  (4表)  │  (限流)
                    └─────────┘
```

---

## 🚀 快速开始

### 前提

- Python ≥ 3.11
- MySQL 8.0
- Redis 7.0 (可选)

### 安装运行

```bash
cd E:\PythonAssistant

# 1. 安装依赖
pip install -r requirements.txt

# 2. 编辑 .env — 填入 API Key
# DEEPSEEK_API_KEY=sk-your-key
# QWEN_API_KEY=sk-your-key (可选)

# 3. 启动
python run.py
# → http://localhost:5000
```

数据库和表首次启动自动创建，内置角色自动写入。

---

## ⚙️ 配置说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FLASK_ENV` | `development` | 运行环境 |
| `DEFAULT_MODEL` | `deepseek` | deepseek / qwen |
| `TEMPERATURE` | `0.7` | 0-1 |
| `MAX_TOKENS` | `2048` | 单次最大 Token |
| `DEEPSEEK_API_KEY` | - | DeepSeek API 密钥 |
| `QWEN_API_KEY` | - | 通义千问 API 密钥 |
| `DATABASE_URL` | MySQL 连接 | 数据库 |
| `REDIS_URL` | `redis://localhost:6379/0` | 限流用 |
| `RATE_LIMIT` | `60` | 每分钟/IP 上限 |

---

## 📡 API 文档

### 通用规范

- 基础路径: `/api/v1`
- 请求/响应: JSON `{code, message, data}`
- 字符编码: UTF-8

### 接口总览 (18个)

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/chat` | 普通对话 |
| `POST` | `/chat/stream` | 流式对话 (SSE) |
| `GET` | `/conversations` | 会话列表 |
| `POST` | `/conversations` | 创建会话 |
| `GET` | `/conversations/{id}` | 会话详情 (含消息) |
| `DELETE` | `/conversations/{id}` | 删除会话 |
| `GET` | `/conversations/{id}/messages` | 会话消息 |
| `GET` | `/roles` | 角色列表 |
| `POST` | `/roles` | 创建角色 |
| `PUT` | `/roles/{id}` | 更新角色 |
| `DELETE` | `/roles/{id}` | 删除角色 |
| `POST` | `/tts` | 文本转语音 |
| `GET` | `/voices` | 可用音色列表 |
| `GET` | `/health` | 健康检查 |
| `GET` | `/models` | 模型列表 |
| `GET` | `/tools` | 工具列表 |
| `POST` | `/tools/{name}` | 执行工具 |

### 对话请求示例

```json
POST /api/v1/chat
{
  "conversation_id": "",
  "message": "你好",
  "model": "deepseek",
  "system_prompt": "你是一位编程老师",
  "role_id": "role-uuid-here"
}
```

### TTS 请求示例

```json
POST /api/v1/tts
{
  "text": "你好，我是智能助手",
  "voice": "xiaoxiao"
}
```

---

## 🎤 语音功能

### 语音输入 (STT)

- 点击输入框旁 🎤 按钮开始说话
- 说完**自动停止并发送**，无需手动操作
- 基于浏览器内置 `SpeechRecognition` API，免费
- 支持中文普通话
- 快捷键：`Ctrl+M`
- 麦克风测试工具：`http://localhost:5000/static/mic-test.html`

### 语音输出 (TTS)

- AI 回复后自动朗读
- 基于 Microsoft Edge TTS（免费，无需 API Key）
- 5 种自然音色：晓晓/云希/晓伊/云扬/晓辰
- 底部可切换音色、开关自动朗读
- 再次点击 🎤 可打断 AI 语音

---

## 🎭 角色系统

### 内置角色 (6个)

| 图标 | 角色 | 场景 |
|------|------|------|
| 🤖 | 通用助手 | 日常问答 |
| 🧑‍🏫 | 编程老师 | 技术教学 |
| 💻 | 软件工程师 | 代码生成 |
| 📊 | 数据分析师 | 数据洞察 |
| ✍️ | 内容创作者 | 文档撰写 |
| 🌐 | 翻译专家 | 中英互译 |

### 自定义角色

- 点击 **"＋ 角色"** → 选图标 → 填名称和提示词 → 保存
- 双击下拉框中的自定义角色可编辑
- 角色存储在数据库，重启不丢失

### 角色-对话绑定

- 每条对话独立绑定创建时的角色
- 切换历史对话，角色下拉框和头像自动恢复
- 选新角色 = 创建全新对话，历史对话不受影响

---

## 🔧 扩展开发

### 添加模型

`app/llm/` 下创建客户端 → 继承 `BaseLLMClient` → `ModelService` 注册

### 添加工具

`app/tools/` 下用 `@tool` 装饰器 → `ToolService._tools` 注册

### 添加 TTS 音色

编辑 `app/api/voice.py` 的 `VOICES` 字典

---

## ❓ 常见问题

| 问题 | 解决 |
|------|------|
| 启动报 MySQL 连接拒绝 | 检查 `.env` 密码是否正确 |
| 模型返回空 | 检查 API Key；`curl /api/v1/health` |
| 流式无打字效果 | Nginx: `proxy_buffering off`；curl: `-N` |
| 语音识别不工作 | 先测麦克风：`/static/mic-test.html` |
| 语音合成失败 | `pip install --upgrade edge-tts` |
| 角色切换后头像不更新 | **Ctrl+F5** 强制刷新 |
| 代码修改不生效 | Flask debug 缓存，重启服务 |
| CORS 错误 | 开发环境默认允许所有 |

---

## 📚 部署文档

详见 [deploy.md](deploy.md) — Gunicorn + Nginx + Docker + HTTPS 完整指南

---

## 📄 许可证

MIT License
