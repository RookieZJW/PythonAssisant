# 🤖 智能助手 (Smart Assistant)

基于 **Flask + LangChain** 的 AI 对话系统。支持**实时 Markdown 渲染**、**3 引擎 TTS**、**浏览器 STT**、**SSE 流式**、**12 套主题 + 自定义**、**角色系统**、**模型参数面板**、**文件上传附件**、**Token 统计**、**对话导出**。

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green)](https://flask.palletsprojects.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-orange)](https://langchain.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-utf8mb4-blue)](https://mysql.com)

---

## ✨ 功能

| 分类 | 功能 |
|------|------|
| 📝 **Markdown** | 流式实时渲染，JSON-SSE 换行保护 |
| 🎤 **语音** | 浏览器 STT 输入 + 火山/腾讯 TTS 11音色 |
| 🎨 **主题** | 12 套预设 + 背景图/视频 + 气泡/按钮/下拉框透明度 |
| 🎭 **角色** | 6 内置 + 自定义，对话绑定，可改名 |
| ⚙️ **参数** | Temperature / MaxTokens / Top-P 面板调节 |
| 📎 **附件** | 上传 PDF/Word/TXT，AI 基于文件回答 |
| 📥 **导出** | 对话导出 Markdown 文件 |
| 📊 **统计** | 每条消息 Token + 侧边栏汇总 |
| 🗑️ **删除** | 硬删除会话+消息，彻底清理 |

---

## 🚀 快速开始

```bash
pip install -r requirements.txt
# .env 填入 DEEPSEEK_API_KEY
python run.py
# → http://localhost:5000
```

---

## ⚙️ 配置

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `QWEN_API_KEY` | 通义千问（可选） |
| `VOLCANO_TTS_APP_ID` / `VOLCANO_TTS_TOKEN` | 火山 TTS（可选） |
| `TENCENT_TTS_SECRET_ID` / `TENCENT_TTS_SECRET_KEY` | 腾讯 TTS（可选） |

---

## 📡 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/chat` / `/chat/stream` | 对话 / 流式 |
| `GET/POST/PUT/DELETE` | `/api/v1/conversations/{id}` | 会话 CRUD + 导出 |
| `GET/POST/PUT/DELETE` | `/api/v1/roles/{id}` | 角色 CRUD |
| `POST` | `/api/v1/tts` | 文本转语音 |
| `POST` | `/api/v1/upload` | 文件上传 |
| `GET` | `/api/v1/stats` | Token 统计 |
| `GET` | `/api/v1/health` / `/models` | 系统 |

---

## 🎨 主题 (12 套)

**暗色**：夜曲 / 极光 / 暮光 / 深海暗流 / 樱吹雪 / 暗烬 / 幽兰 / 矩阵

**亮色**：象牙白 / 抹茶 / 晴空 / 桃气（气泡文字自动暗色）

**自定义**：背景图/视频 · 聊天气泡透明度 · 按钮透明度 · 下拉框透明度 · 输入框透明度 · 边框粗细/颜色 · 气泡阴影

---

## 📚 文档

- [deploy.md](deploy.md) — 生产部署 (Gunicorn + Nginx + Docker + HTTPS)
- [零基础入门指南.md](零基础入门指南.md) — 从零学编程

---

MIT License
