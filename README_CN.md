<p align="center">
  <img src="icon/mkg-icon-512.svg" alt="MKG Logo" width="150">
</p>

<h1 align="center">Meta Knowledge Graph</h1>

<p align="center">
  <strong>简体中文</strong> | <a href="README.md">English</a>
</p>

<p align="center">
  <strong>基于 LLM 的学术知识图谱引擎</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker Ready">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/version-1.2.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" alt="React">
</p>

<p align="center">
  从 PDF 论文自动提取概念层级结构，以交互式力导向图可视化展示
</p>

---

## 演示

### 知识图谱交互

![知识图谱演示](docs/demo.gif)

*功能展示：概念图谱交互 → 点击概念 → 发现研究点 → 概念去重 → 多格式导出*

### 论文上传与处理

![上传演示](docs/upload.gif)

*功能展示：上传 PDF → 批量处理 → 查看提取结果*

---

## 核心特性

| 功能 | 描述 |
|------|------|
| 📄 **PDF 解析** | 自动提取论文标题、作者、摘要等元数据 |
| 🧠 **两阶段概念提取** | Stage 1: 论文理解 → Stage 2: 核心概念提取 |
| 📊 **知识图谱可视化** | 类似 Obsidian/Neo4j 的力导向图交互式展示 |
| 🔍 **研究点发现** | 四种方法论：空白地带、末端延伸、瓶颈识别、迁移应用 |
| 🔄 **智能概念去重** | 三种合并类型：同义词、粒度吸收、翻译对应 |
| 📤 **多格式导出** | 支持 HTML、Obsidian Canvas、Markdown |
| 📁 **文件夹管理** | 可折叠侧边栏，论文分类管理 |

---

## 架构

```
┌─────────────────────────────────────────────────┐
│                  前端                            │
│         React + TypeScript + D3.js               │
└─────────────────────┬───────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────┐
│                  后端                            │
│      FastAPI + SQLite + PyMuPDF                  │
└─────────────────────┬───────────────────────────┘
                      │ LLM API
┌─────────────────────▼───────────────────────────┐
│                 LLM 层                           │
│      Claude / Gemini / Qwen / DeepSeek           │
└─────────────────────────────────────────────────┘
```

**数据流：** `PDF → LLM 提取 (两阶段) → 知识图谱 → 导出`

---

## 快速开始

### Docker 一键部署（推荐）

```bash
docker run -d -p 8088:8088 \
  -e ANTHROPIC_API_KEY=sk-ant-xxx \
  -v ./data:/app/data \
  ghcr.io/seaual/meta-knowledge-graph:latest
```

访问 http://localhost:8088 即可使用。

> 将 `ANTHROPIC_API_KEY` 替换为你的 API Key，也支持 `GOOGLE_API_KEY` 或 `DASHSCOPE_API_KEY`

### 手动部署

<details>
<summary>点击展开详细步骤</summary>

```bash
# 克隆项目
git clone https://github.com/Seaual/meta-knowledge-graph.git
cd meta-knowledge-graph

# 后端配置
python -m venv venv
source venv/bin/activate  # Linux/Mac，Windows 用: venv\Scripts\activate
pip install -r requirements.txt

# 配置 LLM
cp .env.example .env
# 编辑 .env 文件，填入 API Key

# 前端配置
cd frontend && npm install

# 启动服务
python -m uvicorn backend.main:app --port 8088 --reload &
cd frontend && npm run dev
```

</details>

---

## 功能详解

### 两阶段概念提取

```
Stage 1: 论文理解
├── 研究背景识别
├── 核心贡献区分
└── 背景/新概念分类

Stage 2: 概念提取
├── 锚点路径（定位论文归属）
├── 贡献子树（论文真正贡献）
└── 贡献角色标注（proposed/improved/applied/analyzed）
```

### 研究点发现方法论

| 方法 | 描述 |
|------|------|
| 🔍 **空白地带法** | 图谱中两个本应有联系的分支缺少连接 |
| 🌱 **末端延伸法** | 叶子节点能否应用到其他分支 |
| 🔥 **瓶颈识别法** | 某节点连接大量子节点但缺少兄弟节点 |
| 🔄 **迁移应用法** | 成熟方法能否迁移到另一个未解决的问题 |

### 概念层级

| 类别 | 描述 | 示例 |
|------|------|------|
| field | 大领域 | 人工智能、运筹学 |
| direction | 研究方向 | 多智能体强化学习 |
| subdirection | 子方向 | 值分解方法 |
| task | 研究任务 | 信用分配问题 |
| method | 方法/算法 | QMIX |
| technique | 技术细节 | 注意力加权混合 |

---

## 使用说明

### 上传论文
1. 进入「论文」页面
2. 点击上传按钮，选择 PDF 文件（支持批量）
3. 论文将出现在「待处理」列表中

### 处理论文
1. 点击「处理」按钮或「批量处理」
2. LLM 自动提取概念树
3. 概念添加到知识图谱

### 浏览图谱
1. 进入「概念」页面
2. 拖拽节点、滚轮缩放
3. 点击概念查看详情

### 发现研究点
1. 点击概念节点
2. 点击「发现研究点」
3. LLM 分析图谱结构，生成 3-5 个研究方向

### 概念去重
1. 点击「去重扫描」
2. 查看合并建议（同义词/粒度吸收/翻译对应）
3. 执行选中的合并

### 导出图谱
- **HTML** - 交互式 D3.js 力导向图（可独立运行）
- **Canvas** - Obsidian Canvas 格式
- **Markdown** - 双链格式笔记

---

## 支持的 LLM 提供商

| 提供商 | 类型 | 配置方式 |
|--------|------|----------|
| **Anthropic Claude** | 原生 API | `ANTHROPIC_API_KEY` |
| **Claude CLI** | 本地 CLI | 自动检测 |
| **Google Gemini** | 原生 API | `GOOGLE_API_KEY` |
| **阿里云 DashScope** | OpenAI 兼容 | `DASHSCOPE_API_KEY` |
| **OpenRouter** | OpenAI 兼容 | 自定义 base_url |
| **DeepSeek** | OpenAI 兼容 | 自定义 base_url |
| **MiniMax** | OpenAI 兼容 | 自定义 base_url |

---

## 技术栈

**后端：** Python 3.10+ • FastAPI • SQLite • PyMuPDF

**前端：** React 18 • TypeScript • Vite • TailwindCSS • D3.js

**LLM：** Claude / Gemini / Qwen / DeepSeek / OpenRouter

---

## 项目结构

```
meta-knowledge-graph/
├── backend/           # FastAPI 后端
│   ├── main.py        # 应用入口
│   ├── routes/        # API 路由
│   └── schemas.py     # 数据模型
├── frontend/          # React 前端
│   └── src/
│       ├── pages/     # 页面组件
│       └── components/
├── mkg/               # 核心库
│   ├── database.py    # 数据库操作
│   ├── graph.py       # 图谱操作
│   ├── pdf_parser.py  # PDF 解析 & LLM 提取
│   └── dedup/         # 去重模块
├── papers/            # 论文存储
├── icon/              # 项目图标
└── PROMPT_GUIDE.md    # Prompt 工程指南
```

---

## API 文档

启动后访问 http://localhost:8088/docs

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/papers/upload` | POST | 上传 PDF |
| `/api/papers/batch-upload` | POST | 批量上传 |
| `/api/papers/batch-process` | POST | 批量处理 |
| `/api/concepts/` | GET | 获取所有概念 |
| `/api/concepts/{id}/research-points` | GET | 发现研究点 |
| `/api/concepts/dedup/scan` | POST | 扫描重复概念 |
| `/api/graph/export/obsidian/html` | GET | 导出 HTML |

---

## 开发计划

- [x] 支持更多 LLM（DeepSeek、OpenRouter、MiniMax）
- [x] 概念合并与去重
- [x] 多格式导出
- [x] 批量处理
- [x] 两阶段概念提取
- [x] 研究点发现方法论
- [ ] 协作功能
- [ ] Neo4j 支持

---

## 贡献

欢迎 Issue 和 Pull Request！

## 许可证

MIT License

---

<p align="center">
  <img src="icon/mkg-logo-horizontal.svg" alt="MKG Logo" width="200">
</p>

<p align="center">
  Made with ❤️ by <a href="https://github.com/Seaual">Seaual</a>
</p>