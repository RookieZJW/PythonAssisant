# 🤖 Python 多功能智能助手

基于 **Flask + LangChain** 构建的多模型智能对话系统。支持**语音对话**、**SSE 流式响应**、**8 套预设主题**、**多角色系统**、**对话-角色绑定**、**自定义背景**、**工具调用**，自带科技感动画 Web 界面。

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green)](https://flask.palletsprojects.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-orange)](https://langchain.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-utf8mb4-blue)](https://mysql.com)

---

## ✨ 功能特性

| 分类 | 功能 | 说明 |
|------|------|------|
| 🎤 **语音对话** | 浏览器 STT + edge-tts | 说完自动发送，5 种自然音色 |
| 🎨 **主题系统** | 8 套预设 + 全自定义 | 背景图/视频、透明度、阴影、边框 |
| 🎭 **角色系统** | 内置 + 自定义 | 全部可编辑/删除，同名检测，对话绑定 |
| 🤖 **多模型** | DeepSeek / 通义千问 | 一键切换 |
| ⚡ **流式响应** | SSE Token 实时输出 | 打字机效果 |
| 🧠 **对话记忆** | 滑动窗口 + MySQL | 多轮上下文，持久化 |
| 🔧 **工具调用** | 计算器 / 数据分析 / 搜索 | 可扩展插件 |
| 💾 **历史管理** | 侧边栏 + localStorage | 刷新不丢失 |
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

首次启动自动建库建表、写入内置角色。麦克风测试：`/static/mic-test.html`

---

## ⚙️ 配置

| 变量 | 默认 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | - | DeepSeek API 密钥 |
| `QWEN_API_KEY` | - | 通义千问（可选） |
| `DEFAULT_MODEL` | `deepseek` | 默认模型 |
| `TEMPERATURE` | `0.7` | 随机性 |
| `DATABASE_URL` | MySQL | 数据库连接 |
| `REDIS_URL` | `redis://...` | 限流（可选） |

---

## 📡 API（18 个接口）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/chat` | 对话 |
| `POST` | `/api/v1/chat/stream` | 流式对话 SSE |
| `GET/POST` | `/api/v1/conversations` | 会话列表/创建 |
| `GET/DELETE` | `/api/v1/conversations/{id}` | 会话详情/删除 |
| `GET` | `/api/v1/conversations/{id}/messages` | 消息列表 |
| `GET/POST` | `/api/v1/roles` | 角色列表/创建 |
| `PUT/DELETE` | `/api/v1/roles/{id}` | 更新/删除角色 |
| `POST` | `/api/v1/tts` | 文本转语音 |
| `GET` | `/api/v1/voices` | 音色列表 |
| `GET` | `/api/v1/health` | 健康检查 |
| `GET` | `/api/v1/models` | 模型列表 |
| `GET/POST` | `/api/v1/tools/{name}` | 工具列表/执行 |
| `GET` | `/api/v1/local-media?path=` | 本地文件代理 |

---

## 🎨 主题系统

**8 套预设**一键切换：

| 主题 | 风格 |
|------|------|
| 🌙 夜曲 | 灰蓝 + 深黑，安静高级 |
| 🌌 极光 | 青绿 + 靛蓝 + 粉，现代 AI |
| 🌅 暮光 | 暖琥珀 + 深棕，温暖优雅 |
| 🌊 深海 | 天蓝 + 深蓝黑，沉浸深邃 |
| 🌸 樱语 | 玫瑰粉 + 深紫红，柔和精致 |
| 🔥 余烬 | 金橙 + 深黑棕，暖色沉稳 |
| 🟣 虚空 | 淡紫 + 近纯黑，极简神秘 |
| 🟩 黑客帝国 | 亮绿终端 + 纯黑，Matrix |

**自定义**：背景图/视频（支持本地路径）· 面板透明度（0%~100%，仅背景） · 聊天气泡阴影 · 边框粗细/颜色

---

## 🎤 语音

- **输入**：点 🎤 说话 → 自动识别发送（浏览器 `SpeechRecognition`，免费）
- **输出**：AI 回复后自动朗读（`edge-tts`，5 种音色，免费）
- 点击 🎤 可打断正在播放的语音
- 快捷键 `Ctrl+M`
- 麦克风诊断：`/static/mic-test.html`

---

## 🎭 角色

**6 个内置**：通用助手 / 编程老师 / 软件工程师 / 数据分析师 / 内容创作者 / 翻译专家

**自定义**：＋ 角色 → 选图标 → 名称 + 提示词 → 保存（同名检测，重复拒绝）

**编辑/删除**：选中角色后下拉框旁 ✏️🗑️ 按钮，所有角色可改可删（至少保留 1 个）

**对话绑定**：每条对话独立绑定角色，切换历史对话自动恢复对应角色和头像

---

## 📁 项目结构

```
PythonAssistant/
├── run.py                     # 启动
├── requirements.txt           # 依赖
├── .env / .env.example        # 配置
├── Dockerfile / compose.yml   # Docker
├── README.md / deploy.md      # 文档
├── app/
│   ├── __init__.py            # 工厂 + 角色初始化
│   ├── extensions.py          # DB + SocketIO
│   ├── config/settings.py     # 三环境
│   ├── models/                # role, conversation, message, user
│   ├── llm/                   # 策略模式 (DeepSeek/Qwen)
│   ├── services/              # chat, model, tool
│   ├── tools/                 # calculator, analyzer, search
│   ├── api/                   # chat, conversation, role, voice, system
│   ├── middleware/            # auth, rate_limit, logger
│   └── utils/                 # response, exceptions, validators
├── static/                    # index.html, mic-test.html
├── tests/ / logs/ / migrations/
```

---

## 📄 许可证

MIT License
