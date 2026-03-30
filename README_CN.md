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
  <a href="https://github.com/Seaual/meta-knowledge-graph/stargazers"><img src="https://img.shields.io/github/stars/Seaual/meta-knowledge-graph?style=social" alt="Stars" /></a>
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker Ready">
  <img src="https://img.shields.io/github/license/Seaual/meta-knowledge-graph" alt="License">
  <img src="https://img.shields.io/github/v/release/Seaual/meta-knowledge-graph" alt="Release">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/LLM-Claude%20%7C%20Gemini%20%7C%20Qwen-8A2BE2" alt="LLM">
</p>

<p align="center">
  从 PDF 论文自动提取概念层级结构，以交互式力导向图可视化展示
</p>

<p align="center">
  <a href="#快速开始">快速开始</a> •
  <a href="#核心特性">功能</a> •
  <a href="#概念层级">概念体系</a> •
  <a href="#开发计划">Roadmap</a> •
  <a href="https://github.com/Seaual/meta-knowledge-graph/issues">Issues</a>
</p>

---

## v2.0 新特性

| 功能 | 描述 |
|------|------|
| 🎨 **浅色学术风界面** | 温暖的奶油/褐石色调配色，优雅的排版设计（Playfair Display + Source Sans） |
| 🌐 **中英文双语支持** | 完整的中英文界面，自动检测浏览器语言 |
| 📚 **Semantic Scholar 集成** | 自动获取论文元数据（DOI、引用数、期刊、作者等） |
| 🔍 **图谱搜索与筛选** | 按名称搜索概念，按类别筛选并高亮显示 |
| 📊 **类别层级节点大小** | 节点大小按层级递减（领域 → 方向 → ... → 技术） |
| 🎓 **新手引导教程** | 首次使用自动展示功能介绍，附带 10 篇 LLM 经典论文演示数据 |

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
| 📊 **知识图谱可视化** | 类似 Obsidian/Neo4j 的力导向图，节点大小按层级显示 |
| 🔍 **研究点发现** | 四种方法论：空白地带、末端延伸、瓶颈识别、迁移应用 |
| 🔄 **智能概念去重** | 三种合并类型：同义词、粒度吸收、翻译对应 |
| 📤 **多格式导出** | 支持 HTML、Obsidian Canvas、Markdown |
| 📁 **文件夹管理** | 可折叠侧边栏，论文分类管理 |
| ⚡ **队列处理** | 顺序批量处理，实时预估剩余时间 |
| 🌐 **双语界面** | 完整中英文支持，自动检测语言 |
| 📚 **S2 元数据增强** | 自动从 Semantic Scholar 获取论文元数据 |
| 🐳 **Docker 部署** | 一键拉取镜像，快速部署使用 |

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
                      │ LLM API / S2 API
┌─────────────────────▼───────────────────────────┐
│              外部服务                             │
│   LLM: Claude/Gemini/Qwen   S2: 元数据 API       │
└─────────────────────────────────────────────────┘
```

**数据流：** `PDF → S2 元数据增强 → LLM 提取 (两阶段) → 知识图谱 → 导出`

---

## 快速开始

### 一键部署（推荐）

**Linux / Mac:**
```bash
curl -fsSL https://raw.githubusercontent.com/Seaual/meta-knowledge-graph/main/deploy.sh | bash
```

**Windows:**
```cmd
curl -fsSL https://raw.githubusercontent.com/Seaual/meta-knowledge-graph/main/deploy.bat -o deploy.bat && deploy.bat
```

或下载脚本后运行：
- Linux/Mac: `chmod +x deploy.sh && ./deploy.sh`
- Windows: 双击 `deploy.bat`

访问 http://localhost:8088 即可使用。

**配置 LLM**：进入浏览器中的「设置」页面配置 API Key（支持 Claude、OpenAI、Gemini、通义千问、DeepSeek 等）

> 💡 API Key 保存在本地数据库中，无需设置环境变量。

### Docker Compose 部署

```bash
# 克隆项目
git clone https://github.com/Seaual/meta-knowledge-graph.git
cd meta-knowledge-graph/docker

# 启动服务
docker-compose up -d
```

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

# 启动后端
python -m uvicorn backend.main:app --port 8088 --reload &

# 启动前端
cd frontend && npm run dev
```

访问 http://localhost:5173，在「设置」页面配置 API Key。

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

| 类别 | 描述 | 示例 | 节点大小 |
|------|------|------|----------|
| field | 大领域 | 人工智能、运筹学 | 最大 |
| direction | 研究方向 | 多智能体强化学习 | 大 |
| subdirection | 子方向 | 值分解方法 | 中 |
| task | 研究任务 | 信用分配问题 | 小 |
| method | 方法/算法 | QMIX | 较小 |
| technique | 技术细节 | 注意力加权混合 | 最小 |

---

## 使用说明

### 上传论文
1. 进入「论文」页面
2. 点击上传按钮，选择 PDF 文件（支持批量）
3. 论文将出现在「待处理」列表中，自动从 Semantic Scholar 获取元数据

### 处理论文
1. 点击「处理」按钮或「批量处理」
2. LLM 自动提取概念树
3. 概念添加到知识图谱

### 浏览图谱
1. 进入「概念」页面
2. 拖拽节点、滚轮缩放
3. 使用搜索框搜索概念，按类别筛选
4. 点击概念查看详情

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

**外部 API：** Semantic Scholar（论文元数据增强）

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
│       ├── components/
│       └── i18n/      # 国际化（中/英）
├── mkg/               # 核心库
│   ├── database.py    # 数据库操作
│   ├── graph.py       # 图谱操作
│   ├── pdf_parser.py  # PDF 解析 & LLM 提取
│   ├── semantic_scholar.py  # S2 API 客户端
│   └── dedup/         # 去重模块
├── papers/            # 论文存储
├── scripts/           # 工具脚本（演示数据等）
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
| `/api/s2/papers/{doi}/enhance` | POST | 从 S2 增强元数据 |
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
- [x] 浅色学术风界面
- [x] 中英文双语支持
- [x] Semantic Scholar 元数据增强
- [x] 图谱搜索与筛选
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