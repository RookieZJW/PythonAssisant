# 🤖 Python 多功能智能助手

基于 **Flask + LangChain** 构建的多模型智能对话系统。支持**语音对话 (STT + TTS)**、**SSE 流式响应**、**多角色系统**、**对话-角色绑定**、**工具调用**，自带科技感粒子动画 Web 界面。

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green)](https://flask.palletsprojects.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-orange)](https://langchain.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-blue)](https://mysql.com)

---

## 📋 目录

- [功能特性](#-功能特性)
- [快速开始](#-快速开始)
- [配置说明](#-配置说明)
- [API 文档](#-api-文档)
- [语音功能](#-语音功能)
- [角色系统](#-角色系统)
- [工具系统](#-工具系统)
- [项目结构](#-项目结构)
- [系统架构](#-系统架构)
- [部署方案](#-部署方案)
- [扩展开发](#-扩展开发)
- [常见问题](#-常见问题)

---

## ✨ 功能特性

| 分类 | 功能 | 说明 |
|------|------|------|
| 🎤 **语音输入** | 浏览器语音识别 (STT) | 说完成自动发送，免费 |
| 🔊 **语音输出** | Microsoft Edge TTS | 5 种自然中文音色，免费 |
| 🎭 **角色系统** | 6 内置 + 无限自定义 | 全部可编辑/删除，同名检测 |
| 🔗 **对话-角色绑定** | 每条对话独立绑定角色 | 切换对话自动恢复对应角色 |
| 🤖 **多模型** | DeepSeek / 通义千问 | 一键切换 |
| ⚡ **流式响应** | SSE Token 级别实时输出 | 打字机效果 |
| 🧠 **对话记忆** | 滑动窗口 + MySQL 持久化 | 多轮上下文 |
| 🔧 **工具调用** | 计算器 / 数据分析 / 网络搜索 | 可扩展 |
| 🎨 **科技感 UI** | 粒子动画 / 霓虹光效 / 玻璃态 | 深色主题 |
| 💾 **历史持久化** | 侧边栏管理 | 刷新/重开不丢失 |
| 🔐 **安全** | API Key 认证 / Redis 限流 | 生产级 |
| 🐳 **容器化** | Docker + Compose | 一键部署 |

---

## 🚀 快速开始

### 前提

- Python ≥ 3.11
- MySQL 8.0
- Redis 7.0（可选，无 Redis 时限流自动跳过）

### 安装

```bash
cd PythonAssistant
pip install -r requirements.txt
```

### 配置

编辑 `.env`，最少填一个 API Key：

```env
DEEPSEEK_API_KEY=sk-your-key
# QWEN_API_KEY=sk-your-key   # 可选
```

### 运行

```bash
python run.py
# 打开 http://localhost:5000
```

首次启动自动创建数据库和表、写入 6 个内置角色。

### 麦克风测试

```
http://localhost:5000/static/mic-test.html
```

---

## ⚙️ 配置说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FLASK_ENV` | `development` | `development` / `production` / `testing` |
| `DEFAULT_MODEL` | `deepseek` | `deepseek` / `qwen` |
| `TEMPERATURE` | `0.7` | 模型随机性 (0~1) |
| `MAX_TOKENS` | `2048` | 单次最大输出 |
| `DEEPSEEK_API_KEY` | - | DeepSeek API 密钥 |
| `QWEN_API_KEY` | - | 通义千问 API 密钥 |
| `DATABASE_URL` | MySQL 连接 | 数据库连接串 |
| `REDIS_URL` | `redis://localhost:6379/0` | 限流用，可选 |
| `RATE_LIMIT` | `60` | 每分钟每 IP 上限 |

---

## 📡 API 文档

**统一响应格式**: `{"code": 200, "message": "success", "data": {...}}`

### 对话 (3 个)

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/chat` | 普通对话 |
| `POST` | `/api/v1/chat/stream` | 流式对话 (SSE) |

```json
// 请求
{"message":"你好","model":"deepseek","system_prompt":"你是一位老师","role_id":"uuid"}
// 响应
{"code":200,"data":{"conversation_id":"...","answer":"你好！","model":"deepseek-chat"}}
```

### 会话管理 (5 个)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/conversations` | 列表 `?page=1&page_size=20` |
| `POST` | `/api/v1/conversations` | 创建 `{"title":"聊天","role_id":"uuid"}` |
| `GET` | `/api/v1/conversations/{id}` | 详情含消息 |
| `DELETE` | `/api/v1/conversations/{id}` | 软删除 |
| `GET` | `/api/v1/conversations/{id}/messages` | 消息列表 `?limit=20` |

### 角色管理 (4 个)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/roles` | 所有角色 |
| `POST` | `/api/v1/roles` | 创建 `{"name":"角色名","prompt":"提示词","icon":"🎯"}` |
| `PUT` | `/api/v1/roles/{id}` | 更新（全部可编辑） |
| `DELETE` | `/api/v1/roles/{id}` | 删除（全部可删） |

> 创建时自动检测同名，重复返回 409

### 语音 (2 个)

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/tts` | 文本转语音 `{"text":"你好","voice":"xiaoxiao"}` |
| `GET` | `/api/v1/voices` | 可用音色列表 |

### 系统 (4 个)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/health` | 健康检查 |
| `GET` | `/api/v1/models` | 模型列表 |
| `GET` | `/api/v1/tools` | 工具列表 |
| `POST` | `/api/v1/tools/{name}` | 执行工具 |

---

## 🎤 语音功能

### 语音输入 (STT)

- 点击输入框旁 **🎤** 按钮开始说话
- 说完**自动停止、自动识别、自动发送**
- 基于浏览器 `SpeechRecognition` API，免费，无需 API Key
- 输入框实时显示识别文字，随时可手动编辑
- 快捷键：**Ctrl+M**

### 语音输出 (TTS)

- AI 回复完成后**自动朗读**
- 基于 **Microsoft Edge TTS**，免费，无需 API Key
- 5 种自然音色，底部下拉框可切换：

| Key | 音色 | 风格 |
|-----|------|------|
| `xiaoxiao` | 晓晓 | 女声·温柔 |
| `yunxi` | 云希 | 男声·阳光 |
| `xiaoyi` | 晓伊 | 女声·活泼 |
| `yunyang` | 云扬 | 男声·沉稳 |
| `xiaochen` | 晓辰 | 女声·温柔 |

- 可关闭"自动朗读"（取消勾选）
- 再次点击 🎤 可**打断 AI 语音**

### 麦克风测试工具

```
http://localhost:5000/static/mic-test.html
```

- 音量条可视化
- 设备选择器
- 录音回放验证

---

## 🎭 角色系统

### 内置角色 (6 个)

| 图标 | 角色 | 适用场景 |
|------|------|----------|
| 🤖 | 通用助手 | 日常问答 |
| 🧑‍🏫 | 编程老师 | 技术教学、概念讲解 |
| 💻 | 软件工程师 | 代码生成、架构设计 |
| 📊 | 数据分析师 | 数据洞察、统计报告 |
| ✍️ | 内容创作者 | 文档撰写、文案创作 |
| 🌐 | 翻译专家 | 中英互译 |

### 自定义角色

1. 点击右上角 **"＋ 角色"**
2. 选择图标 → 填写名称和提示词 → 保存
3. **角色名称不能重复**，重复会提示错误

### 编辑/删除角色

- 选中角色后，下拉框旁出现 ✏️ 和 🗑️ 按钮
- **所有角色**（含内置）均可编辑和删除
- 至少保留 1 个角色，最后一个不可删除
- 删除后自动切换到剩余第一个角色

### 对话-角色绑定

- 每条对话**独立绑定**创建时的角色
- 点击历史对话 → 角色下拉框和头像**自动恢复**
- 选新角色 = 创建全新对话，历史对话不受影响
- 侧边栏每条对话显示对应的**角色图标**

---

## 🔧 工具系统

| 工具 | 功能 | 触发方式 |
|------|------|----------|
| 🧮 计算器 | 数学表达式求值 | API: `POST /api/v1/tools/calculator` |
| 📊 数据分析 | JSON 数据统计分析 | API: `POST /api/v1/tools/data_analyzer` |
| 🔍 网络搜索 | DuckDuckGo 搜索 | API: `POST /api/v1/tools/web_search` |

---

## 📁 项目结构

```
PythonAssistant/
├── run.py                    # 🚀 启动入口 (SocketIO)
├── gunicorn_config.py        # ⚙️ 生产 WSGI 配置
├── requirements.txt          # 📦 依赖清单
├── .env / .env.example       # 🔐 环境变量
├── Dockerfile                # 🐳 Docker 镜像
├── docker-compose.yml        # 🐳 Docker 编排
├── README.md                 # 📖 本文档
├── deploy.md                 # 🚀 部署文档
│
├── app/
│   ├── __init__.py           #   应用工厂 + 内置角色初始化
│   ├── extensions.py         #   Flask 扩展 (DB + SocketIO)
│   │
│   ├── config/
│   │   ├── settings.py       #   三环境配置
│   │   └── prompts.py        #   Prompt 模板库
│   │
│   ├── models/               # 🗄️ 数据模型 (4 表)
│   │   ├── role.py           #   角色
│   │   ├── conversation.py   #   会话 (绑定 role_id)
│   │   ├── message.py        #   消息
│   │   └── user.py           #   用户
│   │
│   ├── llm/                  # 🧠 大模型层 (策略模式)
│   │   ├── base.py           #   抽象基类
│   │   ├── deepseek_client.py
│   │   ├── qwen_client.py
│   │   └── memory.py         #   滑动窗口记忆
│   │
│   ├── services/             # 💼 业务逻辑
│   │   ├── chat_service.py
│   │   ├── model_service.py
│   │   └── tool_service.py
│   │
│   ├── tools/                # 🔧 工具插件
│   │   ├── calculator.py
│   │   ├── data_analyzer.py
│   │   └── web_search.py
│   │
│   ├── api/                  # 🌐 路由 (5 蓝图, 18 接口)
│   │   ├── chat.py
│   │   ├── conversation.py
│   │   ├── role.py
│   │   ├── voice.py
│   │   └── system.py
│   │
│   ├── middleware/           # 🛡️ 中间件
│   │   ├── auth.py
│   │   ├── rate_limit.py
│   │   └── logger.py
│   │
│   └── utils/                # 🧰 工具
│       ├── response.py
│       ├── exceptions.py
│       └── validators.py
│
├── static/                   # 🌐 前端
│   ├── index.html            #   主界面 (SPA + 粒子 + 语音)
│   └── mic-test.html         #   麦克风诊断
│
├── tests/                    # 🧪 测试
├── logs/                     # 📝 日志
└── migrations/               # 🔄 迁移
```

---

## 🏗 系统架构

```
  浏览器
  ├── SpeechRecognition (STT, 免费)
  ├── 粒子动画 UI
  └── Audio API (播放 TTS)
       │
       ├── HTTP REST / SSE / WebSocket
       │
       ▼
  Flask + SocketIO (Python)
  ├── API 路由层 (5 蓝图)
  ├── 业务服务层 (对话 / 模型 / 工具)
  ├── LLM 调用层 (DeepSeek / Qwen)
  ├── edge-tts CLI (TTS, 免费)
  └── 中间件 (认证 / 限流 / 日志)
       │
       ▼
  MySQL 8.0 (utf8mb4)
  ├── roles
  ├── conversations (role_id → 角色绑定)
  ├── messages
  └── users

  Redis 7.0 (限流, 可选)
```

---

## 🚢 部署方案

详细见 **[deploy.md](deploy.md)**，三种方案：

| 方案 | 适用 | 命令 |
|------|------|------|
| 开发模式 | 本地使用 | `python run.py` |
| Gunicorn + Nginx | 生产 | `gunicorn -c gunicorn_config.py run:app` |
| Docker | 快速部署 | `docker compose up -d` |

### 生产关键配置

```nginx
# Nginx SSE 支持（必须）
proxy_buffering off;
proxy_read_timeout 300s;
```

---

## 🔧 扩展开发

| 需求 | 方法 |
|------|------|
| 添加模型 | `app/llm/` 继承 `BaseLLMClient` → `ModelService` 注册 |
| 添加工具 | `app/tools/` `@tool` 装饰器 → `ToolService._tools` 注册 |
| 添加 TTS 音色 | 编辑 `app/api/voice.py` 的 `VOICES` |
| 添加 API | `app/api/` 创建蓝图 → `__init__.py` 注册 |

---

## ❓ 常见问题

| 问题 | 解决 |
|------|------|
| MySQL 连接拒绝 | 检查 `.env` 密码是否正确 |
| 模型返回空 | 检查 API Key；`curl /api/v1/health` |
| 流式输出无打字效果 | Nginx `proxy_buffering off`；curl `-N` |
| 语音识别不工作 | 先测麦克风 `/static/mic-test.html`；检查 Win+I 隐私设置 |
| 语音合成失败 | `pip install --upgrade edge-tts` |
| Emoji 导致消息存储报错 | 已修：所有表改为 `utf8mb4` |
| 角色切换后头像不变 | **Ctrl+F5** 强制刷新 |
| 代码修改不生效 | Flask debug 自动重载有缓存问题，重启服务 |
| CORS 跨域错误 | 开发环境默认允许所有 |

---

## 📄 许可证

MIT License
