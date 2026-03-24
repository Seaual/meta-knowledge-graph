<p align="center">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker Ready">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/version-1.1.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" alt="React">
</p>

<h1 align="center">Meta Knowledge Graph</h1>

<p align="center">
  <strong>基于 LLM 的学术知识图谱引擎</strong><br>
  <sub>LLM-powered Academic Knowledge Graph Engine</sub>
</p>

<p align="center">
  从 PDF 论文自动提取概念层级结构，以交互式力导向图可视化展示<br>
  Extract hierarchical concepts from PDF papers with interactive force-directed visualization
</p>

---

## Demo

![Demo](docs/demo.gif)

*展示功能：上传论文 → 知识图谱交互 → 发现研究点 → 概念去重 → 多格式导出*

## 架构 / Architecture

```
┌─────────────────────────────────────────────────┐
│                  Frontend                        │
│         React + TypeScript + D3.js               │
└─────────────────────┬───────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────┐
│                  Backend                         │
│      FastAPI + SQLite + PyMuPDF                  │
└─────────────────────┬───────────────────────────┘
                      │ LLM API
┌─────────────────────▼───────────────────────────┐
│                 LLM Layer                        │
│         Claude / Gemini / Qwen                   │
└─────────────────────────────────────────────────┘
```

**数据流 / Data Flow:** `PDF → LLM Extract → Knowledge Graph → Export`

## 快速开始 / Quick Start

### Docker 一键部署 / Docker Deployment

```bash
docker run -d -p 8088:8088 \
  -e ANTHROPIC_API_KEY=sk-ant-xxx \
  -v ./data:/app/data \
  ghcr.io/seaual/meta-knowledge-graph:latest
```

访问 http://localhost:8088 即可使用。

> 将 `ANTHROPIC_API_KEY` 替换为你的 API Key，也支持 `GOOGLE_API_KEY` 或 `DASHSCOPE_API_KEY`

### 手动部署 / Manual Setup

<details>
<summary>点击展开详细步骤</summary>

#### 1. 克隆项目

```bash
git clone https://github.com/Seaual/meta-knowledge-graph.git
cd meta-knowledge-graph
```

#### 2. 后端配置

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

#### 3. 配置 LLM

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入 API Key（三选一）：

```env
# Claude API（推荐）
ANTHROPIC_API_KEY=sk-ant-...

# Google AI Studio
GOOGLE_API_KEY=...

# 阿里云 DashScope
DASHSCOPE_API_KEY=...
```

#### 4. 前端配置

```bash
cd frontend
npm install
```

#### 5. 启动服务

**Windows:**
```bash
start.bat
```

**手动启动:**
```bash
# 后端
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8088 --reload

# 前端（新终端）
cd frontend && npm run dev
```

访问 http://localhost:5173

</details>

## 功能特性 / Features

| 功能 | 描述 |
|------|------|
| 📄 **PDF 解析** | 自动提取论文标题、作者、摘要等元数据 |
| 🧠 **LLM 概念提取** | 使用 Claude/Gemini/Qwen 提取层次化概念结构 |
| 📊 **知识图谱可视化** | 类似 Obsidian/Neo4j 的力导向图交互式展示 |
| 🔄 **批量处理** | 多 PDF 并行上传与队列处理 |
| 🔍 **研究点发现** | 基于图谱分析发现潜在研究方向 |
| 🔄 **概念去重** | 智能扫描重复概念，LLM 分析合并建议 |
| 📤 **多格式导出** | 支持 HTML、Obsidian Canvas、Markdown |

## 使用说明 / Usage

### 上传论文 / Upload Papers

1. 进入「论文」页面
2. 点击上传按钮，选择 PDF 文件
3. 论文将出现在「待处理」列表中

### 处理论文 / Process Papers

1. 点击「处理」按钮
2. LLM 自动提取概念树
3. 概念添加到知识图谱

### 浏览图谱 / Browse Graph

1. 进入「概念」页面
2. 拖拽节点、滚轮缩放
3. 点击概念查看详情

### 发现研究点 / Discover Research Points

1. 点击概念节点
2. 点击「发现研究点」
3. LLM 生成 3-5 个潜在研究方向

### 概念去重 / Deduplication

1. 点击「去重扫描」
2. 查看合并建议
3. 执行选中的合并

### 导出图谱 / Export Graph

- **HTML** - 交互式 D3.js 力导向图
- **Canvas** - Obsidian Canvas 格式
- **Markdown** - 双链格式笔记

## 技术栈 / Tech Stack

**Backend:** Python 3.10+ • FastAPI • SQLite • PyMuPDF

**Frontend:** React 18 • TypeScript • Vite • TailwindCSS • D3.js

**LLM:** Claude API / Google AI / DashScope

## 项目结构 / Project Structure

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
├── openclaw/          # 核心库
│   ├── database.py    # 数据库
│   ├── graph.py       # 图谱操作
│   └── pdf_parser.py  # PDF 解析
└── papers/            # 论文存储
```

## API 文档 / API Docs

启动后访问 http://localhost:8088/docs

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/papers/upload` | POST | 上传 PDF |
| `/api/papers/batch-upload` | POST | 批量上传 |
| `/api/concepts/` | GET | 获取所有概念 |
| `/api/concepts/dedup/scan` | POST | 扫描重复概念 |
| `/api/graph/export/obsidian/html` | GET | 导出 HTML |

## 概念层级 / Concept Hierarchy

| 类别 | 描述 | 示例 |
|------|------|------|
| field | 大领域 | 运筹学、人工智能 |
| direction | 研究方向 | 车辆路径问题 |
| method | 方法/算法 | 模拟退火 |
| technique | 技术细节 | 值函数近似 |

## 开发计划 / Roadmap

- [ ] 支持更多 LLM（DeepSeek、OpenRouter）
- [x] 概念合并与去重
- [x] 多格式导出
- [x] 批量处理
- [ ] 协作功能
- [ ] Neo4j 支持

## 贡献 / Contributing

欢迎 Issue 和 Pull Request！

## 许可证 / License

MIT License

---

# English Version

<p align="center">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker Ready">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/version-1.1.0-blue" alt="Version">
</p>

<h1 align="center">Meta Knowledge Graph</h1>

<p align="center">
  <strong>LLM-powered Academic Knowledge Graph Engine</strong>
</p>

<p align="center">
  Automatically extract hierarchical concepts from PDF papers with interactive force-directed graph visualization
</p>

---

## Demo

![Demo](docs/demo.gif)

*Features: Upload PDFs → Interactive Knowledge Graph → Research Point Discovery → Deduplication → Multi-format Export*

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Frontend                        │
│         React + TypeScript + D3.js               │
└─────────────────────┬───────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────┐
│                  Backend                         │
│      FastAPI + SQLite + PyMuPDF                  │
└─────────────────────┬───────────────────────────┘
                      │ LLM API
┌─────────────────────▼───────────────────────────┐
│                 LLM Layer                        │
│         Claude / Gemini / Qwen                   │
└─────────────────────────────────────────────────┘
```

**Data Flow:** `PDF → LLM Extract → Knowledge Graph → Export`

## Quick Start

### Docker (Recommended)

```bash
docker run -d -p 8088:8088 \
  -e ANTHROPIC_API_KEY=sk-ant-xxx \
  -v ./data:/app/data \
  ghcr.io/seaual/meta-knowledge-graph:latest
```

Open http://localhost:8088

### Manual Setup

<details>
<summary>Click to expand</summary>

```bash
# Clone
git clone https://github.com/Seaual/meta-knowledge-graph.git
cd meta-knowledge-graph

# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure LLM
cp .env.example .env
# Edit .env with your API key

# Frontend
cd frontend && npm install

# Start
python -m uvicorn backend.main:app --port 8088 &
cd frontend && npm run dev
```

</details>

## Features

| Feature | Description |
|---------|-------------|
| 📄 **PDF Parsing** | Extract title, authors, abstract automatically |
| 🧠 **LLM Extraction** | Hierarchical concept extraction with Claude/Gemini/Qwen |
| 📊 **Visualization** | Obsidian/Neo4j-style force-directed graph |
| 🔄 **Batch Processing** | Parallel PDF upload and processing |
| 🔍 **Research Discovery** | Find potential research directions from graph |
| 🔄 **Deduplication** | Smart duplicate detection with LLM merge suggestions |
| 📤 **Export** | HTML, Obsidian Canvas, Markdown formats |

## Usage

1. **Upload Papers** - Go to Papers page, upload PDFs
2. **Process** - Click process to extract concepts with LLM
3. **Explore Graph** - Drag nodes, zoom, click for details
4. **Discover Research Points** - LLM analyzes graph for research opportunities
5. **Deduplicate** - Scan and merge duplicate concepts
6. **Export** - Download as HTML/Canvas/Markdown

## Tech Stack

**Backend:** Python 3.10+ • FastAPI • SQLite • PyMuPDF

**Frontend:** React 18 • TypeScript • Vite • TailwindCSS • D3.js

**LLM:** Claude API / Google AI / DashScope

## Roadmap

- [ ] More LLM backends (DeepSeek, OpenRouter)
- [x] Concept deduplication
- [x] Multi-format export
- [x] Batch processing
- [ ] Collaboration features
- [ ] Neo4j support

## Contributing

Issues and Pull Requests welcome!

## License

MIT License