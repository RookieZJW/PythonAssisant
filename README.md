# 🤖 Python 多功能智能助手 v2.6

基于 **Flask + LangChain** 的全栈 AI 对话系统。支持**用户登录注册**、**SSE 流式 Markdown**、**双引擎 TTS**、**12 套主题**、**角色绑定**、**文件附件**。

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green)](https://flask.palletsprojects.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-orange)](https://langchain.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-utf8mb4-blue)](https://mysql.com)

---

## 📋 目录

1. [功能特性](#1-功能特性)
2. [快速开始](#2-快速开始)
3. [配置说明](#3-配置说明)
4. [使用教程](#4-使用教程)
5. [API 接口](#5-api-接口)
6. [项目结构](#6-项目结构)
7. [部署方案](#7-部署方案)
8. [扩展开发](#8-扩展开发)
9. [常见问题](#9-常见问题)

---

## 1. 功能特性

| 分类 | 功能 |
|------|------|
| 🔐 **登录系统** | 用户名密码注册/登录，Session 认证，用户数据隔离 |
| 📱 **预留登录** | 手机验证码、微信/QQ扫码（UI就绪，需企业资质） |
| 🤖 **双模型** | DeepSeek + 通义千问，策略模式一键切换 |
| ⚡ **流式 SSE** | Token 级实时输出，JSON-SSE 换行保护 |
| 📝 **Markdown** | 流式实时渲染，代码高亮+一键复制 |
| 🎤 **语音** | 浏览器 STT 输入 + 火山/腾讯 TTS（11音色） |
| 🎭 **角色** | 6内置+自定义，对话-角色绑定，用户隔离 |
| 🎨 **主题** | 12套预设，透明度/阴影/边框可调，背景图/视频+历史 |
| 📎 **附件** | PDF/Word/TXT上传，AI基于内容回答 |
| ⚙️ **参数** | Temperature/MaxTokens/Top-P 滑块面板 |
| 📊 **统计** | 每条消息Token + 今日/累计用量 |
| 📥 **导出** | 对话导出Markdown文件 |
| 🗑️ **管理** | 会话硬删除+改名，角色全部可编辑 |

---

## 2. 快速开始

### 2.1 环境要求

- Python ≥ 3.11
- MySQL 8.0（需运行中）
- （可选）Redis 7.0

### 2.2 安装

```bash
cd E:\PythonAssistant
pip install -r requirements.txt
```

### 2.3 配置

编辑 `.env`，至少填入 DeepSeek API Key：

```env
DEEPSEEK_API_KEY=sk-你的密钥
# 可选：通义千问
# QWEN_API_KEY=sk-你的密钥
```

数据库首次启动自动创建。

### 2.4 启动

```bash
python run.py
```

浏览器打开 **http://localhost:5000** → 自动跳转登录页 → 注册账号 → 开始聊天。

### 2.5 生产部署

```bash
gunicorn -c gunicorn_config.py run:app
```

详见 [deploy.md](deploy.md)。

---

## 3. 配置说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | - | DeepSeek API Key（必填） |
| `QWEN_API_KEY` | - | 通义千问（可选） |
| `DEFAULT_MODEL` | `deepseek` | 默认模型 |
| `TEMPERATURE` | `0.7` | 0=严谨 2=创意 |
| `MAX_TOKENS` | `2048` | 回复最大长度 |
| `DATABASE_URL` | MySQL连接串 | 数据库 |
| `REDIS_URL` | `redis://localhost:6379/0` | 限流（可选） |
| `VOLCANO_TTS_APP_ID/TOKEN` | - | 火山TTS（可选） |
| `TENCENT_TTS_SECRET_ID/KEY` | - | 腾讯TTS（可选） |
| `RATE_LIMIT` | `60` | 每分钟/IP上限 |

---

## 4. 使用教程

### 4.1 注册登录

打开 http://localhost:5000/login → 点击"没有账号？立即注册" → 输入用户名（≥2位）和密码（≥6位）→ 自动跳转聊天页。

> 手机验证码、微信/QQ扫码登录 UI 已就绪，因需企业营业执照暂不可用。

每个用户登录后只能看到**自己的**对话、角色和背景历史。

### 4.2 对话

- 输入框打字 → **Enter** 发送（Shift+Enter 换行）
- AI 逐字流式回复，带 Markdown 实时排版
- 输出过程中发送按钮变红色 ⏹，点击停止
- 顶部 **🔄 模型** 切换 DeepSeek/通义千问

### 4.3 角色

- 顶部下拉框选角色，AI 回复风格随之变化
- **＋ 角色**：自定义名称/图标/提示词（同名拒绝重复）
- 选择角色后 ✏️ 编辑 / 🗑️ 删除
- 对话自动绑定角色，切换历史对话恢复对应角色

### 4.4 语音

- 点击输入框旁 **🎤** 说话 → 自动识别发送
- AI 回复完成后自动朗读（可关闭）
- 底部下拉框切换音色（火山8种 + 腾讯3种）
- 🔊 手动朗读 / ⏹ 停止
- 麦克风测试：`/static/mic-test.html`

### 4.5 主题

- 顶栏 **🎨 主题** → 12 套预设一键切换
- 透明度调节：聊天气泡/按钮/下拉框/输入框（背景透明，文字不变）
- 边框粗细/颜色 + 气泡阴影
- 自定义背景：输入图片/视频 URL → 类型选图片/视频 → 模式选全屏/仅聊天区 → 点应用
- 支持本地路径（如 `D:\图片\bg.jpg`）
- 💾 存入历史，下次点击直接切换

### 4.6 附件

- 输入框旁 **📎** → 选文件（PDF/Word/TXT/代码）
- 按钮变绿 📄 → 输入基于附件的问题
- 再次点击移除附件

### 4.7 模型参数

- **⚙️ 参数** → Temperature/MaxTokens/Top-P 滑块
- 数值实时生效，localStorage 持久化

### 4.8 对话管理

- **左侧边栏**：查看所有历史对话，点击切换
- **✏️** 按钮：重命名对话标题
- **✕** 按钮：删除（含数据库消息）
- **📥 导出** 按钮：下载当前对话为 Markdown 文件

---

## 5. API 接口

**统一响应**：`{"code": 200, "message": "success", "data": {...}}`

| 蓝图 | 方法 | 路径 | 说明 |
|------|------|------|------|
| **auth** | POST | `/api/v1/auth/register` | 注册 |
| | POST | `/api/v1/auth/login` | 登录 |
| | GET | `/api/v1/auth/me` | 当前用户 |
| | POST | `/api/v1/auth/logout` | 退出 |
| **chat** | POST | `/api/v1/chat` | 对话 |
| | POST | `/api/v1/chat/stream` | 流式对话(SSE) |
| **conversation** | GET/POST | `/api/v1/conversations` | 列表/创建 |
| | GET/PUT/DELETE | `/api/v1/conversations/{id}` | 详情/改名/删除 |
| | GET | `/api/v1/conversations/{id}/messages` | 消息 |
| | GET | `/api/v1/conversations/{id}/export` | 导出MD |
| **role** | GET/POST | `/api/v1/roles` | 列表/创建 |
| | PUT/DELETE | `/api/v1/roles/{id}` | 更新/删除 |
| **voice** | POST | `/api/v1/tts` | 文本转语音 |
| | GET | `/api/v1/voices` | 音色列表 |
| **system** | GET | `/api/v1/health` | 健康检查 |
| | GET | `/api/v1/models` | 模型列表 |
| | GET | `/api/v1/stats` | Token统计 |
| | GET | `/api/v1/local-media?path=` | 本地文件代理 |
| **upload** | POST | `/api/v1/upload` | 文件上传 |
| **background** | GET/POST/DELETE | `/api/v1/backgrounds/{id}` | 背景历史 |

### 对话请求示例

```json
POST /api/v1/chat
{
  "message": "帮我写个快速排序",
  "model": "deepseek",
  "conversation_id": "",
  "system_prompt": "你是一位软件工程师",
  "role_id": "role-uuid",
  "params": {"temperature": 0.5, "max_tokens": 1024}
}
```

### TTS 请求示例

```json
POST /api/v1/tts
{
  "text": "你好",
  "voice": "v-xiaoyuan"
}
```

---

## 6. 项目结构

```
PythonAssistant/
├── run.py                     # 启动入口
├── gunicorn_config.py         # 生产WSGI
├── requirements.txt           # 依赖
├── .env / .env.example        # 配置
├── Dockerfile / compose.yml   # Docker
├── README.md                  # 本文档
├── deploy.md                  # 部署文档
├── data/
│   └── database_schema.sql    # MySQL表结构
├── app/
│   ├── __init__.py            # 工厂+登录保护
│   ├── extensions.py          # DB+SocketIO
│   ├── config/                # settings, prompts
│   ├── models/                # user/role/conversation/message/background
│   ├── llm/                   # 策略模式 (DeepSeek/Qwen)
│   ├── services/              # chat/model/tool
│   ├── api/                   # 8个蓝图 (auth/chat/conversation/role/voice/system/upload/background)
│   ├── tools/                 # 计算器/数据分析/搜索
│   ├── middleware/            # 认证/限流/日志
│   └── utils/                 # 响应/异常/校验
└── static/                    # 前端 (index.html/login.html/mic-test.html/resume.html)
```

---

## 7. 部署方案

### 方案一：开发模式

```bash
python run.py
```

### 方案二：Gunicorn + Nginx（生产）

```bash
gunicorn -c gunicorn_config.py run:app
```

Nginx 配置关键点：
```nginx
proxy_buffering off;     # SSE 流式必须
proxy_read_timeout 300s; # 长连接
```

### 方案三：Docker

```bash
docker compose up -d
```

详见 **[deploy.md](deploy.md)**

---

## 8. 扩展开发

| 需求 | 方法 |
|------|------|
| 添加模型 | `app/llm/` 继承 `BaseLLMClient` → `ModelService` 注册 |
| 添加工具 | `app/tools/` 用 `@tool` 装饰器 → `ToolService._tools` 注册 |
| 添加TTS音色 | 编辑 `app/api/voice.py` 的 `VOICES` 字典 |
| 添加API | `app/api/` 创建蓝图 → `__init__.py` 注册 |

---

## 9. 常见问题

| 问题 | 解决 |
|------|------|
| MySQL连接拒绝 | 检查MySQL是否运行，`.env`密码是否正确 |
| AI不回复 | 检查API Key；`curl /api/v1/health` |
| 流式无打字效果 | Nginx需 `proxy_buffering off` |
| 语音识别不工作 | `/static/mic-test.html` 诊断；检查浏览器麦克风权限 |
| Markdown渲染异常 | **Ctrl+F5** 强制刷新 |
| 代码修改不生效 | 重启服务 `python run.py` |
| 背景图不显示 | 类型选视频时模式选"全屏显示" |
| Emoji报错 | 数据库表需 utf8mb4 编码 |

---

## 📄 相关资源

- [部署文档](deploy.md)
- [数据库结构](data/database_schema.sql)
- GitHub: https://github.com/RookieZJW/PythonAssisant

MIT License
