# 🤖 Python 多功能智能助手

基于 **Flask + LangChain** 构建的多模型智能对话系统，支持**三引擎 TTS 语音合成**、**浏览器语音输入 STT**、**SSE 流式响应**、**8 套预设主题**、**多角色系统**、**对话-角色绑定**、**自定义背景**，自带科技感粒子动画 Web 界面。

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green)](https://flask.palletsprojects.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-orange)](https://langchain.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-utf8mb4-blue)](https://mysql.com)

---

## ✨ 功能特性

| 分类 | 功能 | 说明 |
|------|------|------|
| 🎤 **语音输入** | 浏览器 SpeechRecognition | 说完自动发送，免费 |
| 🔊 **语音输出** | Edge / 火山 / 腾讯 三引擎 | 14 种音色，多引擎切换 |
| 🎨 **主题系统** | 8 套预设 + 全自定义 | 背景图/视频、透明度、阴影、边框 |
| 🎭 **角色系统** | 6 内置 + 无限自定义 | 全部可编辑/删除，同名检测，对话绑定 |
| 🤖 **多模型** | DeepSeek / 通义千问 | 一键切换 |
| ⚡ **流式响应** | SSE Token 实时输出 | 打字机效果 |
| 🧠 **对话记忆** | 滑动窗口 + MySQL | 多轮上下文，持久化 |
| 🔧 **工具调用** | 计算器 / 数据分析 / 搜索 | 可扩展插件 |
| 💾 **历史管理** | 侧边栏 + localStorage | 角色绑定，刷新不丢 |
| 🔐 **安全** | API Key + Redis 限流 | 生产级 |
| 🐳 **容器化** | Docker + Compose | 一键部署 |

---

## 🚀 快速开始

```bash
cd PythonAssistant
pip install -r requirements.txt
# 编辑 .env 填入 DEEPSEEK_API_KEY
python run.py
# → http://localhost:5000
```

首次启动自动建库建表、写入内置角色。麦克风诊断：`/static/mic-test.html`

---

## ⚙️ 配置项

| 变量 | 默认 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | - | DeepSeek API 密钥 |
| `QWEN_API_KEY` | - | 通义千问（可选） |
| `DEFAULT_MODEL` | `deepseek` | 默认模型 |
| `TEMPERATURE` | `0.7` | 随机性 0~1 |
| `MAX_TOKENS` | `2048` | 单次最大 Token |
| `DATABASE_URL` | MySQL | 数据库连接 |
| `REDIS_URL` | - | 限流（可选） |
| `VOLCANO_TTS_APP_ID` | - | 火山 TTS（可选） |
| `VOLCANO_TTS_TOKEN` | - | 火山 TTS（可选） |
| `TENCENT_TTS_SECRET_ID` | - | 腾讯 TTS（可选） |
| `TENCENT_TTS_SECRET_KEY` | - | 腾讯 TTS（可选） |

---

## 📡 API（19 个接口）

### 对话 (2)
| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/chat` | 普通对话 |
| `POST` | `/api/v1/chat/stream` | 流式对话 SSE |

### 会话管理 (5)
| `GET` | `/api/v1/conversations` | 列表 |
| `POST` | `/api/v1/conversations` | 创建 |
| `GET` | `/api/v1/conversations/{id}` | 详情含消息 |
| `DELETE` | `/api/v1/conversations/{id}` | 软删除 |
| `GET` | `/api/v1/conversations/{id}/messages` | 消息 |

### 角色管理 (4)
| `GET` | `/api/v1/roles` | 列表 |
| `POST` | `/api/v1/roles` | 创建（同名检测） |
| `PUT` | `/api/v1/roles/{id}` | 更新 |
| `DELETE` | `/api/v1/roles/{id}` | 删除 |

### 语音合成 (2)
| `POST` | `/api/v1/tts` | 文本转语音 |
| `GET` | `/api/v1/voices` | 音色列表（3 引擎 14 种） |

### 系统 (4)
| `GET` | `/api/v1/health` | 健康检查 |
| `GET` | `/api/v1/models` | 模型列表 |
| `GET` | `/api/v1/tools` | 工具列表 |
| `POST` | `/api/v1/tools/{name}` | 执行工具 |
| `GET` | `/api/v1/local-media?path=` | 本地文件代理 |

**统一响应**：`{"code": 200, "message": "success", "data": {...}}`

---

## 🎤 语音功能

### 语音输入（STT）

- 点击 🎤 → 说话 → 自动识别并发送
- 浏览器 `SpeechRecognition` API，免费
- 实时转写显示，可手动编辑
- 快捷键 `Ctrl+M`
- 麦克风诊断：`/static/mic-test.html`（音量条 + 录音回放）

### 语音输出（TTS）— 3 引擎 14 音色

| 引擎 | 音色 | 费用 |
|------|------|------|
| 🟢 **Edge** | 晓晓 / 云希 / 晓伊 / 云扬 / 晓辰 | 免费 |
| 🟣 **火山引擎** | 小源 / 大夏 / 清心 / 知行 / 彤彤 | 免费额度 |
| 🔵 **腾讯云** | 智聆 / 智瑜 / 智美 / 智云 | 100 万字符/月免费 |

- AI 回复后自动朗读
- 底部下拉框切换音色/引擎
- 可关闭"自动朗读"
- 再次点击 🎤 打断语音

---

## 🎨 主题系统

**8 套预设**一键切换：

| 主题 | 风格 |
|------|------|
| 🌙 夜曲 | 灰蓝 + 深黑，安静高级 |
| 🌌 极光 | 青绿靛蓝粉，现代 AI 感 |
| 🌅 暮光 | 暖琥珀 + 深棕，温暖优雅 |
| 🌊 深海 | 天蓝深蓝，沉浸深邃 |
| 🌸 樱语 | 玫瑰粉紫，柔和精致 |
| 🔥 余烬 | 金橙深黑，暖色沉稳 |
| 🟣 虚空 | 淡紫近纯黑，极简神秘 |
| 🟩 黑客帝国 | 亮绿终端 + 纯黑，Matrix |

**自定义**：背景图/视频（支持本地 D:\ 路径）· 面板透明度（仅背景）· 气泡阴影（大小/颜色）· 边框（粗细/颜色）

---

## 🎭 角色系统

**6 个内置**：通用助手 / 编程老师 / 软件工程师 / 数据分析师 / 内容创作者 / 翻译专家

- **＋ 角色**：创建自定义角色，同名自动拒绝
- **✏️🗑️**：所有角色可编辑/删除（至少保留 1 个）
- **对话绑定**：每条对话独立绑定角色，切换自动恢复

---

## 📁 项目结构

```
PythonAssistant/
├── run.py                          # 启动入口
├── gunicorn_config.py              # 生产 WSGI
├── requirements.txt                # 依赖
├── .env / .env.example             # 配置
├── Dockerfile / docker-compose.yml # Docker
├── README.md / deploy.md           # 文档
├── app/
│   ├── __init__.py                 # 工厂 + 角色初始化
│   ├── extensions.py               # DB + SocketIO
│   ├── config/                     # settings, prompts
│   ├── models/                     # role, conversation, message, user
│   ├── llm/                        # 策略模式 (DeepSeek/Qwen)
│   ├── services/                   # chat, model, tool
│   ├── tools/                      # calculator, analyzer, search
│   ├── api/                        # chat, conversation, role, voice, system
│   ├── middleware/                 # auth, rate_limit, logger
│   └── utils/                      # response, exceptions, validators
├── static/                         # index.html, mic-test.html
├── tests/ / logs/ / migrations/
```

---

## 🚢 部署

详见 **[deploy.md](deploy.md)** — Gunicorn + Nginx + Docker + HTTPS 完整指南

### 快速部署

```bash
# Docker
docker compose up -d

# 传统
gunicorn -c gunicorn_config.py run:app
```

### SSE 关键配置

```nginx
proxy_buffering off;
proxy_read_timeout 300s;
```

---

## ❓ 常见问题

| 问题 | 解决 |
|------|------|
| MySQL 连接拒绝 | 检查 `.env` 密码 |
| 模型返回空 | 检查 API Key |
| 流式无效果 | Nginx: `proxy_buffering off` |
| 语音不识别 | `/static/mic-test.html` 诊断 |
| Emoji 报错 | 已修：全表 `utf8mb4` |
| 主题失效 | **Ctrl+F5** 强制刷新 |
| 代码不生效 | 重启服务 |

---

## 📄 许可证

MIT License
