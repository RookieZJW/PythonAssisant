# 🤖 Python 多功能智能助手

基于 **Flask + LangChain** 构建的多模型智能对话系统。支持 **SSE 流式响应**、**多角色切换**、**自定义角色**、**对话历史持久化**、**工具调用**，自带科技感动画 Web 界面。

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green)](https://flask.palletsprojects.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-orange)](https://langchain.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-blue)](https://mysql.com)
[![Redis](https://img.shields.io/badge/Redis-7.0-red)](https://redis.io)

---

## 📋 目录

- [功能特性](#-功能特性)
- [界面预览](#-界面预览)
- [技术栈](#-技术栈)
- [项目结构](#-项目结构)
- [系统架构](#-系统架构)
- [快速开始](#-快速开始)
- [配置说明](#-配置说明)
- [API 文档](#-api-文档)
- [使用方法](#-使用方法)
- [扩展开发](#-扩展开发)
- [常见问题](#-常见问题)

---

## ✨ 功能特性

| 分类 | 功能 | 说明 |
|------|------|------|
| 🎭 **多角色系统** | 6 个内置角色 + 自定义角色 | 一键切换角色，自定义名称/图标/提示词 |
| 💬 **对话管理** | 历史记录持久化 | 左侧边栏管理，切换/删除对话，刷新不丢失 |
| 🤖 **多模型支持** | DeepSeek / 通义千问 | 统一接口，一键切换模型 |
| ⚡ **流式响应** | SSE Token 级实时输出 | 打字机效果，体验流畅 |
| 🧠 **对话记忆** | 滑动窗口 + MySQL 持久化 | 多轮上下文记忆，跨会话保留 |
| 🔧 **工具调用** | 计算器 / 数据分析 / 网络搜索 | 可扩展的插件系统 |
| 🎨 **科技感 UI** | 粒子背景 / 霓虹光效 / 动画 | 深色科技风，动态粒子连线 |
| 🔐 **安全防护** | API Key 认证 / Redis 滑动窗口限流 | 生产级安全 |
| 🐳 **容器部署** | Docker / Docker Compose | 一键部署 |
| 📊 **生产就绪** | Gunicorn + gevent + Nginx | 多进程异步，SSE 友好 |

---

## 🖥 界面预览

```
┌────────────┬──────────────────────────────────┐
│  ⚡AI      │  🎭 [角色选择▼]  DeepSeek  🔄 ＋ │
│  v2.0      ├──────────────────────────────────┤
│            │                                  │
│  💬 对话1   │  🤖  你好！选一个角色开始聊天     │
│  💬 对话2   │      左侧可切换历史对话           │
│  💬 对话3   │                                  │
│            │      用户消息 ▸                  │
│            │                                  │
│ ────────── ├──────────────────────────────────│
│ ✦ 新对话    │  [输入消息...]              ↑  │
└────────────┴──────────────────────────────────┘
        动态粒子背景 + 霓虹发光特效
```

### 内置角色

| 图标 | 角色 | 适用场景 |
|------|------|----------|
| 🤖 | 通用助手 | 日常问答、信息查询 |
| 🧑‍🏫 | 编程老师 | 技术教学、概念讲解 |
| 💻 | 软件工程师 | 代码生成、架构设计 |
| 📊 | 数据分析师 | 数据洞察、统计分析 |
| ✍️ | 内容创作者 | 文档撰写、内容创作 |
| 🌐 | 翻译专家 | 中英互译、术语保留 |

### 自定义角色

点击 **"＋ 角色"** 按钮 → 选择图标 → 填写名称和提示词 → 保存。

> 自定义角色存储在数据库中，重启不丢失。双击下拉框中的自定义角色可编辑。

---

## 🛠 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **Web 框架** | Flask | 3.x | HTTP 服务、路由、蓝图 |
| | Flask-CORS | 6.x | 跨域资源共享 |
| **LLM** | LangChain | 1.x | 模型编排、Prompt 管理 |
| | LangChain-DeepSeek | 1.x | DeepSeek 官方集成 |
| | LangChain-Community | 0.4.x | 通义千问社区集成 |
| **大模型** | DeepSeek | deepseek-chat | 默认对话模型 |
| | 通义千问 (DashScope) | qwen-plus | 备选对话模型 |
| **数据库** | MySQL | 8.0 | 会话 / 消息 / 用户 / 角色存储 |
| | SQLAlchemy | 2.x | Python ORM |
| | PyMySQL | 1.x | MySQL 驱动 |
| **缓存** | Redis | 7.0 | 滑动窗口限流计数器 |
| **前端** | 原生 HTML/CSS/JS | - | 零依赖，单文件 SPA |
| **部署** | Gunicorn | 22.x | WSGI 生产服务器 |
| | Gevent | 24.x | 异步 Worker（SSE 必需） |

---

## 📁 项目结构

```
smart-assistant/
│
├── run.py                        # 🚀 应用启动入口
├── gunicorn_config.py            # ⚙️ Gunicorn 生产配置
├── requirements.txt              # 📦 Python 依赖清单
├── .env / .env.example           # 🔐 环境变量（API Key / 数据库）
├── .gitignore
├── Dockerfile                    # 🐳 Docker 镜像
├── docker-compose.yml            # 🐳 Docker 编排
├── README.md                     # 📖 项目文档（本文件）
├── deploy.md                     # 🚀 部署文档
│
├── app/                          # 🏗️ 应用主目录
│   ├── __init__.py               #   应用工厂 + 内置角色初始化
│   ├── extensions.py             #   Flask 扩展（DB 自动创建）
│   │
│   ├── config/                   # ⚙️ 配置模块
│   │   ├── settings.py           #   三环境：development / production / testing
│   │   └── prompts.py            #   Prompt 模板库
│   │
│   ├── models/                   # 🗄️ 数据模型（4 张表）
│   │   ├── role.py               #   角色模型（内置 + 自定义）
│   │   ├── conversation.py       #   会话模型（软删除 / 分页）
│   │   ├── message.py            #   消息模型（user / assistant / system）
│   │   └── user.py               #   用户模型（API Key 认证）
│   │
│   ├── llm/                      # 🧠 大模型调用层（策略模式）
│   │   ├── base.py               #   抽象基类
│   │   ├── deepseek_client.py    #   DeepSeek 客户端
│   │   ├── qwen_client.py        #   通义千问客户端
│   │   └── memory.py             #   滑动窗口对话记忆
│   │
│   ├── services/                 # 💼 业务逻辑层
│   │   ├── chat_service.py       #   对话流程编排
│   │   ├── model_service.py      #   模型工厂 + 单例缓存
│   │   └── tool_service.py       #   工具注册 / 执行
│   │
│   ├── tools/                    # 🔧 工具插件
│   │   ├── calculator.py         #   数学计算（安全命名空间）
│   │   ├── data_analyzer.py      #   数据分析（Pandas 统计）
│   │   └── web_search.py         #   网络搜索（DuckDuckGo）
│   │
│   ├── api/                      # 🌐 API 路由（4 个蓝图）
│   │   ├── chat.py               #   /chat, /chat/stream
│   │   ├── conversation.py       #   /conversations CRUD
│   │   ├── role.py               #   /roles CRUD（自定义角色）
│   │   └── system.py             #   /health, /models, /tools
│   │
│   ├── middleware/               # 🛡️ 中间件
│   │   ├── auth.py               #   API Key 认证
│   │   ├── rate_limit.py         #   Redis 滑动窗口限流
│   │   └── logger.py             #   请求日志
│   │
│   └── utils/                    # 🧰 工具函数
│       ├── response.py           #   统一 JSON 响应 {code, message, data}
│       ├── exceptions.py         #   自定义异常 + 全局错误处理
│       └── validators.py         #   JSON 参数校验
│
├── static/                       # 🌐 前端
│   └── index.html                #   单文件 SPA（粒子动画 / 角色 / 对话）
│
├── tests/                        # 🧪 测试
│   ├── conftest.py               #   pytest Fixtures
│   ├── test_chat.py              #   对话接口测试
│   └── test_models.py            #   模型 + 会话 API 测试
│
├── logs/                         # 📝 日志目录
└── migrations/                   # 🔄 数据库迁移
```

---

## 🏗 系统架构

```
                          ┌──────────────────────┐
                          │     浏览器 / 客户端    │
                          │  (SSE 流式 + 粒子 UI)  │
                          └──────┬───────┬───────┘
                                 │       │
                           HTTP  │       │ SSE 流
                                 │       │
                          ┌──────▼───────▼───────┐
                          │  Nginx (生产环境)      │
                          │  反向代理 + SSL 终端    │
                          │  proxy_buffering off  │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  Gunicorn + gevent   │
                          │  WSGI 多 Worker       │
                          └──────────┬──────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
     ┌────────▼──────┐  ┌───────────▼──────┐  ┌───────────▼──┐
     │  API 路由层    │  │   业务服务层      │  │   中间件      │
     │  chat / roles │  │  ChatService     │  │  Auth / 限流  │
     │  conv / system│  │  ModelService    │  │  Logger       │
     └────────┬──────┘  │  ToolService     │  └──────────────┘
              │         └────────┬────────┘
              │                  │
     ┌────────▼──────────────────▼──────┐
     │         LLM 调用层                │
     │  DeepSeek Client / Qwen Client   │
     │  策略模式 · 统一接口               │
     └────────┬─────────────────┬───────┘
              │                 │
     ┌────────▼──────┐  ┌───────▼──────┐
     │   MySQL 8.0   │  │   Redis 7    │
     │ ────────────  │  │  限流计数器   │
     │ · roles       │  └──────────────┘
     │ · conversations│
     │ · messages    │
     │ · users       │
     └───────────────┘
```

### 分层职责

| 层级 | 职责 | 依赖 |
|------|------|------|
| **API 路由层** (4 蓝图) | 接收请求、参数校验、响应格式化 | ↓ 服务层 |
| **业务服务层** | 核心逻辑编排、模型调度、工具管理 | ↓ LLM 层 / 模型层 |
| **LLM 调用层** (策略模式) | 统一 invoke/stream/ainvoke 接口 | ↓ 外部 API |
| **数据模型层** (4 表) | ORM 映射、持久化 | ↓ MySQL |
| **中间件层** | 认证、限流、日志等横切关注点 | 独立 |

---

## 🚀 快速开始

### 前提条件

- **Python** ≥ 3.11
- **MySQL** 8.0（需运行中）
- **Redis** 7.0（可选，无 Redis 时限流自动降级）

### 1. 创建虚拟环境

```bash
cd E:\PythonAssistant
python -m venv venv

# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

编辑 `.env` 文件（已预配置 MySQL，仅需填入 API Key）：

```env
# 必填：至少配置一个模型的 API Key
DEEPSEEK_API_KEY=sk-your-key-here     # https://platform.deepseek.com
QWEN_API_KEY=sk-your-key-here         # https://dashscope.aliyun.com (可选)

# 以下已预配置，通常无需修改
FLASK_ENV=development
DATABASE_URL=mysql+pymysql://root:密码@localhost:3306/smart_assistant
REDIS_URL=redis://localhost:6379/0
```

### 4. 启动服务

```bash
python run.py
```

```
 * Running on http://127.0.0.1:5000
 * Running on http://10.x.x.x:5000
```

数据库和表会在首次启动时**自动创建**，内置角色也会自动写入。

### 5. 打开浏览器

访问 **http://localhost:5000** 即可开始聊天。

---

## ⚙️ 配置说明

### 环境切换

| 环境 | `FLASK_ENV` | 数据库 | DEBUG | 说明 |
|------|-------------|--------|-------|------|
| 开发 | `development` | MySQL smart_assistant | ✅ | 默认 |
| 生产 | `production` | MySQL (DATABASE_URL) | ❌ | 见 deploy.md |
| 测试 | `testing` | SQLite 内存 | - | pytest 使用 |

### 关键配置项

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_MODEL` | `deepseek` | 默认模型：deepseek / qwen |
| `TEMPERATURE` | `0.7` | 模型温度（0-1） |
| `MAX_TOKENS` | `2048` | 单次最大输出 Token |
| `DEEPSEEK_API_KEY` | - | DeepSeek API 密钥 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek 模型名 |
| `QWEN_API_KEY` | - | 阿里云 DashScope API 密钥 |
| `QWEN_MODEL` | `qwen-plus` | 通义千问模型名 |
| `DATABASE_URL` | MySQL 连接串 | 数据库连接 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis（限流用） |
| `RATE_LIMIT` | `60` | 每分钟单 IP 请求上限 |

---

## 📡 API 文档

### 通用规范

| 项 | 值 |
|----|-----|
| 基础路径 | `/api/v1` |
| 请求格式 | `Content-Type: application/json` |
| 响应格式 | `{"code": 200, "message": "success", "data": {...}}` |
| 认证 | `X-API-Key` 请求头（可选） |

### 接口总览

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/chat` | 普通对话（同步） |
| `POST` | `/api/v1/chat/stream` | 流式对话（SSE 打字机效果） |
| `GET` | `/api/v1/conversations` | 会话列表（分页） |
| `POST` | `/api/v1/conversations` | 创建会话 |
| `GET` | `/api/v1/conversations/{id}` | 会话详情（含消息） |
| `DELETE` | `/api/v1/conversations/{id}` | 删除会话（软删除） |
| `GET` | `/api/v1/conversations/{id}/messages` | 会话消息 |
| `GET` | `/api/v1/roles` | 角色列表（内置 + 自定义） |
| `POST` | `/api/v1/roles` | 创建自定义角色 |
| `PUT` | `/api/v1/roles/{id}` | 更新自定义角色 |
| `DELETE` | `/api/v1/roles/{id}` | 删除自定义角色 |
| `GET` | `/api/v1/health` | 健康检查 |
| `GET` | `/api/v1/models` | 可用模型列表 |
| `GET` | `/api/v1/tools` | 工具列表 |
| `POST` | `/api/v1/tools/{name}` | 执行工具 |

### 对话接口

```http
POST /api/v1/chat
Content-Type: application/json

{
  "conversation_id": "uuid-or-empty",
  "message": "用 Python 写快速排序",
  "model": "deepseek",
  "system_prompt": "你是一位资深软件工程师"
}
```

```json
{
  "code": 200,
  "data": {
    "conversation_id": "f24aba9c-...",
    "answer": "以下是快速排序的实现：\n\ndef quicksort(arr):\n    ...",
    "model": "deepseek-chat"
  }
}
```

### 流式对话（SSE）

```http
POST /api/v1/chat/stream
```

响应为 `text/event-stream`：
```
data: 以下
data: 是
data: 快速
data: 排序
data: [DONE]
```

### 角色管理

```bash
# 获取所有角色
GET /api/v1/roles

# 创建自定义角色
POST /api/v1/roles
{
  "name": "法律顾问",
  "prompt": "你是一位经验丰富的法律顾问，请基于中国法律...",
  "icon": "⚖️"
}

# 更新角色
PUT /api/v1/roles/{id}

# 删除角色（内置角色不可删除）
DELETE /api/v1/roles/{id}
```

---

## 💡 使用方法

### Web 界面

```
http://localhost:5000
```

- **角色切换**：顶部下拉框选择
- **创建角色**：右上角 "＋ 角色" 按钮
- **编辑角色**：双击下拉框中的自定义角色
- **历史对话**：左侧边栏点击切换
- **新对话**：左下角 "✦ 新对话" 按钮
- **切换模型**：右上角 "🔄 模型" 按钮
- **发送消息**：Enter 发送，Shift+Enter 换行

### 命令行

```bash
# 健康检查
curl http://localhost:5000/api/v1/health

# 对话（默认角色）
curl -X POST http://localhost:5000/api/v1/chat \
  -H "Content-Type: application/json" \
  --data-raw '{"message":"1+1等于几"}'

# 流式对话（-N 禁用缓冲）
curl -N -X POST http://localhost:5000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  --data-raw '{"message":"讲个笑话"}'

# 角色管理
curl http://localhost:5000/api/v1/roles
curl -X POST http://localhost:5000/api/v1/roles \
  -H "Content-Type: application/json" \
  --data-raw '{"name":"诗人","prompt":"你是一位浪漫主义诗人","icon":"🎨"}'
```

### Python SDK

```python
import requests

# 流式对话
resp = requests.post('http://localhost:5000/api/v1/chat/stream', json={
    'message': '写一首诗',
    'system_prompt': '你是一位浪漫主义诗人',
}, stream=True)

for line in resp.iter_lines():
    if line:
        text = line.decode('utf-8')
        if text.startswith('data: '):
            chunk = text[6:]
            if chunk == '[DONE]': break
            print(chunk, end='', flush=True)
```

---

## 🔧 扩展开发

### 添加新模型

1. 在 `app/llm/` 创建客户端 → 继承 `BaseLLMClient`
2. 实现 `invoke` / `stream` / `ainvoke` / `get_model_name`
3. 在 `ModelService` 中注册
4. 在 `settings.py` 添加配置项

### 添加新工具

1. 在 `app/tools/` 创建文件 → 使用 `@tool` 装饰器
2. 在 `ToolService._tools` 中注册

### 添加新角色

直接在 Web 界面 **"＋ 角色"** 创建，或调用 API：

```bash
curl -X POST http://localhost:5000/api/v1/roles \
  -H "Content-Type: application/json" \
  --data-raw '{"name":"角色名","prompt":"角色提示词","icon":"🎯"}'
```

---

## ❓ 常见问题

| 问题 | 解决 |
|------|------|
| 启动报 MySQL 连接拒绝 | 检查 `.env` 中密码是否正确（含特殊字符） |
| 模型返回空 | 检查 API Key；`curl /api/v1/health` 确认模型可用 |
| 流式无打字效果 | Nginx 需 `proxy_buffering off`；curl 需 `-N` |
| CORS 跨域错误 | 开发环境默认允许所有；生产配置 `CORS_ORIGINS` |
| Redis 未安装 | 不影响对话，限流自动降级跳过 |
| 界面文字竖排 | 已修复，Ctrl+F5 强制刷新 |
| 重置数据库 | `DROP DATABASE smart_assistant; CREATE DATABASE ...` |
| 内置角色被删 | 重启应用自动恢复 |

---

## 📚 相关文档

- [deploy.md](deploy.md) — 生产环境部署（Gunicorn + Nginx + Docker + HTTPS）

---

## 📄 许可证

MIT License
