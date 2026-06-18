# 🤖 智能助手 (Smart Assistant)

基于 **Flask + LangChain** 的智能对话系统。支持**实时 Markdown 渲染**、**3 引擎 TTS 语音**、**浏览器 STT 语音输入**、**SSE 流式响应**、**12 套主题**、**角色系统**、**模型参数面板**、**Token 统计**。

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green)](https://flask.palletsprojects.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-orange)](https://langchain.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-utf8mb4-blue)](https://mysql.com)

---

## ✨ 功能

| 分类 | 功能 | 说明 |
|------|------|------|
| 📝 **Markdown** | 代码高亮 + 一键复制 | 流式输出实时排版，JSON-SSE 换行保护 |
| 🎤 **语音输入** | 浏览器 SpeechRecognition | 说完自动发送 |
| 🔊 **语音输出** | 火山 + 腾讯 双引擎 | 11 种音色，失败自动兜底 |
| 🎨 **主题** | 8 暗色 + 4 亮色 | 背景图/视频、透明度、气泡阴影 |
| 🎭 **角色** | 6 内置 + 自定义 | 对话绑定、同名检测 |
| ⚙️ **模型参数** | Temperature/MaxTokens/Top-P | 滑块实时调节 |
| 📊 **Token 统计** | 每条消息 + 侧边栏汇总 | 今日/累计用量 |
| 🤖 **多模型** | DeepSeek / 通义千问 | 一键切换 |
| ⚡ **流式** | SSE 逐字输出 | 打字机效果 |
| 🔧 **工具** | 计算器/数据分析/搜索 | 可扩展 |

---

## 🚀 快速开始

```bash
pip install -r requirements.txt
# .env 填入 DEEPSEEK_API_KEY
python run.py
# → http://localhost:5000
```

---

## ⚙️ 配置项

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `QWEN_API_KEY` | 通义千问（可选） |
| `VOLCANO_TTS_APP_ID` / `VOLCANO_TTS_TOKEN` | 火山 TTS（可选） |
| `TENCENT_TTS_SECRET_ID` / `TENCENT_TTS_SECRET_KEY` | 腾讯 TTS（可选） |
| `DATABASE_URL` | MySQL 连接 |
| `REDIS_URL` | 限流（可选） |

---

## 📡 API (20 个)

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/chat` | 对话 |
| `POST` | `/api/v1/chat/stream` | 流式 SSE |
| `GET/POST` | `/api/v1/conversations` | 会话列表/创建 |
| `GET/DELETE` | `/api/v1/conversations/{id}` | 详情/删除 |
| `GET/POST` | `/api/v1/roles` | 角色列表/创建 |
| `PUT/DELETE` | `/api/v1/roles/{id}` | 更新/删除 |
| `POST` | `/api/v1/tts` | 文本转语音 |
| `GET` | `/api/v1/voices` | 音色列表 |
| `GET` | `/api/v1/stats` | Token 统计 |
| `GET` | `/api/v1/health` | 健康检查 |
| `GET` | `/api/v1/models` | 模型列表 |
| `GET` | `/api/v1/local-media?path=` | 本地文件代理 |

---

## 🎤 TTS 音色 (11 个)

| 引擎 | 音色 |
|------|------|
| 🟣 火山 | 小源/大夏/清心/知行/知性/彤彤/大庆/小艾 |
| 🔵 腾讯 | 智瑜/智美/智聆精品 |

---

## 🎨 主题 (12 套)

**暗色**：夜曲/极光/暮光/深海/樱语/余烬/虚空/黑客帝国

**亮色**：象牙白/薄荷奶绿/天空蓝/玫瑰雾粉

---

## 📁 项目结构

```
PythonAssistant/
├── run.py                     # 启动入口
├── app/
│   ├── api/                   # chat/conversation/role/voice/system
│   ├── models/                # conversation/message/role/user
│   ├── services/              # chat/model/tool
│   ├── llm/                   # deepseek/qwen/memory
│   ├── config/                # settings/prompts
│   ├── tools/                 # calculator/analyzer/search
│   ├── middleware/            # auth/rate_limit/logger
│   └── utils/                 # response/exceptions/validators
├── static/                    # index.html/mic-test.html
└── docs/                      # README/deploy/入门指南
```

---

## 📚 文档

- [deploy.md](deploy.md) — 生产部署
- [零基础入门指南.md](零基础入门指南.md) — 从零学编程

---

## 📄 License

MIT
