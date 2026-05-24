<p align="center">
  <img src="icon/mkg-icon-512.svg" alt="MKG Logo" width="150">
</p>

<h1 align="center">Meta Knowledge Graph</h1>

<p align="center">
  <a href="README.md">English</a> | <strong>简体中文</strong>
</p>

<p align="center">
  <strong>AI 研究助手 — LLM 驱动的学术知识图谱引擎</strong>
</p>

<p align="center">
  <a href="https://github.com/Seaual/meta-knowledge-graph/stargazers"><img src="https://img.shields.io/github/stars/Seaual/meta-knowledge-graph?style=social" alt="Stars"></a>
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/github/license/Seaual/meta-knowledge-graph" alt="License">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/LLM-Claude%20%7C%20Gemini%20%7C%20Qwen-8A2BE2" alt="LLM">
</p>

<p align="center">
  上传论文 PDF → LLM 自动提取层次化概念 →<br>
  构建可交互知识图谱 → AI Agent 发现研究机会
</p>

<p align="center">
  <a href="#快速开始">快速开始</a> •
  <a href="#核心特性">核心特性</a> •
  <a href="#ai-代理系统">AI 代理</a> •
  <a href="#架构">架构</a> •
  <a href="#路线图">路线图</a>
</p>

---

## 核心特性

| 特性 | 描述 |
|------|------|
| 📄 **PDF 解析** | 自动提取论文标题、作者、摘要（MarkItDown，无需 Java） |
| 🌍 **自动翻译** | LLM 驱动的双语概念名（中/英），支持跨语言搜索 |
| 🧠 **两阶段概念提取** | 阶段一：论文理解 → 阶段二：8 类别层次化概念提取 |
| 🌐 **Semantic Scholar 集成** | 自动增强论文元数据（DOI、引用数、期刊、被引次数） |
| 📊 **交互式图谱可视化** | 力导向图 + 类别节点大小 + 搜索筛选 |
| 🔍 **研究点发现** | 4 种方法论：填补空白、叶子延伸、瓶颈突破、迁移应用 |
| 🏷️ **研究点徽章** | 难度、新颖性、潜在影响彩色徽章直观显示 |
| 📤 **多格式导出** | HTML 交互式图谱、Obsidian Canvas、Markdown 双链 |
| 📁 **文件夹管理** | 侧边栏分类组织论文 |
| ⚡ **队列处理** | 顺序批量处理 + 时间预估 |
| 🔄 **智能去重** | 同义词合并、吸收、翻译检测 |
| 🤖 **AI 研究代理** | 基于聊天的论文问答、引用分析、深度研究 |

---

## 演示

### 知识图谱浏览

![知识图谱浏览](docs/概念浏览.gif)

*拖拽节点、缩放、搜索概念、按类别筛选*

### 研究点发现

![研究点发现](docs/研究点发现.gif)

*点击概念 → 发现研究点 → 查看分析上下文*

### 功能概览

![功能展示](docs/功能展示.gif)

*上传 PDF → 处理 → 探索图谱 → 导出*

### LLM 配置

![配置 LLM](docs/配置LLM.gif)

*配置 API Key → 测试连接 → 开始处理*

---

## 快速开始

### 方式一：Docker（推荐）

```bash
docker pull danceinsophy/meta-knowledge-graph:latest
docker run -d -p 8089:8089 \
  -v mkg-data:/app/data \
  -v mkg-papers:/app/papers \
  --restart unless-stopped \
  danceinsophy/meta-knowledge-graph:latest
```

打开 http://localhost:8089，在 **设置** 页面配置 LLM API Key。

> API Key 保存在本地数据库中，无需配置环境变量。支持 Claude、OpenAI、Gemini、Qwen、DeepSeek 等。

#### Docker 安全部署（生产环境）

将 MKG 暴露到公网时，建议启用 Basic Auth：

```bash
docker run -d -p 8089:8089 \
  -e BASIC_AUTH_USER=admin \
  -e BASIC_AUTH_PASSWORD=your-strong-password \
  -v mkg-data:/app/data \
  -v mkg-papers:/app/papers \
  --restart unless-stopped \
  danceinsophy/meta-knowledge-graph:latest
```

或使用 Nginx 反向代理 + HTTPS：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8089;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 方式二：Docker Compose

```bash
git clone https://github.com/Seaual/meta-knowledge-graph.git
cd meta-knowledge-graph/docker
docker-compose up -d
```

### 方式三：手动安装

```bash
# 克隆
git clone https://github.com/Seaual/meta-knowledge-graph.git
cd meta-knowledge-graph

# 后端
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8089 --reload

# 前端（另一个终端）
cd frontend && npm install && npm run dev
```

开发环境访问 http://localhost:5173，享受热更新体验。

---

## AI 代理系统

MKG 内置了基于 LangGraph 的多代理系统，提供智能研究辅助：

### 路由代理（Lead Node）
自动将你的问题分派给专业代理：
- **概念搜索** — 在知识图谱中查找概念
- **论文搜索** — 按标题或概念查找论文
- **论文推荐** — 推荐相关论文

### 论文问答代理
回答关于特定论文的详细问题：
- 从数据库获取论文元数据
- 必要时读取论文全文
- 基于论文内容给出准确回答并注明来源

### 引用分析代理
分析论文的引用关系：
- 引用统计与趋势
- 关键引用论文及其影响
- 集合内的引用网络

### 研究代理
深入分析概念与研究机会：
- 获取概念图谱结构（父子概念）
- 使用 4 种方法论分析研究空白
- 从 Semantic Scholar 推荐前沿论文

### 深度研究
异步运行的多维度研究合成：
- 按维度启动专业研究代理
- 综合发现生成完整报告
- 通过会话 ID 跟踪进度

### 汇总节点
自动将冗长的代理输出精炼为简洁摘要。

---

## 架构

```
┌─────────────────────────────────────────────────┐
│                   前端                           │
│         React + TypeScript + D3.js               │
└─────────────────────┬───────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────┐
│                   后端                           │
│      FastAPI + SQLite + LangGraph Agents         │
└─────────────────────┬───────────────────────────┘
                      │ LLM API / S2 API
┌─────────────────────▼───────────────────────────┐
│                 外部服务                         │
│   LLM: Claude/Gemini/Qwen   S2: 元数据 API       │
└─────────────────────────────────────────────────┘
```

**数据流：** `PDF → S2 增强 → LLM 提取（两阶段） → 知识图谱 → Agent 分析`

### 概念层级

| 类别 | 描述 | 示例 | 节点大小 |
|------|------|------|----------|
| field | 主要领域 | 人工智能 | 最大 |
| direction | 研究方向 | 多智能体强化学习 | 大 |
| subdirection | 子方向 | 价值分解 | 中 |
| task | 研究任务 | 信用分配 | 小 |
| method | 算法 | QMIX | 较小 |
| technique | 技术细节 | 注意力加权混合 | 最小 |
| dataset | 基准/数据集 | ImageNet, SMAC | 中 |
| finding | 关键发现 | 缩放定律 | 中 |

### 研究发现方法

| 方法 | 描述 |
|------|------|
| 🔍 **填补空白** | 相关分支间缺失的连接 |
| 🌱 **叶子延伸** | 叶子节点应用到其他分支 |
| 🔥 **瓶颈突破** | 子节点多但兄弟节点少的节点 |
| 🔄 **迁移应用** | 成熟方法迁移到未解决的问题 |

---

## 使用指南

### 1. 上传论文
- 进入 **论文** 页面 → 上传 PDF 文件（支持批量）
- 论文出现在 **待处理** 列表，Semantic Scholar 自动增强元数据

### 2. 处理论文
- 点击 **处理** 或 **批量处理**
- LLM 提取带中英双语名称的概念树
- 概念合并到知识图谱中

### 3. 探索图谱
- 进入 **概念** 页面 → 拖拽节点、滚动缩放
- 按名称搜索概念，按类别筛选
- 点击任意概念查看详情

### 4. 发现研究点
- 点击概念 → **发现研究点**
- LLM 分析图谱结构，生成 3-5 个研究方向

### 5. 与代理对话
- 进入 **聊天** 页面 → 提问关于论文或概念的问题
- 代理自动路由到合适的专家，返回结构化结果和交互式卡片

### 6. 去重
- 点击 **去重扫描** → 查看合并建议 → 执行选中的合并

### 7. 导出
- **HTML** — 独立交互式 D3.js 图谱
- **Canvas** — Obsidian Canvas 格式
- **Markdown** — 双链笔记格式

---

## 支持的 LLM 提供商

| 提供商 | 类型 | 配置 |
|--------|------|------|
| **Anthropic Claude** | 原生 API | `ANTHROPIC_API_KEY` |
| **Google Gemini** | 原生 API | `GOOGLE_API_KEY` |
| **OpenAI** | OpenAI 兼容 | `OPENAI_API_KEY` |
| **阿里 DashScope** | OpenAI 兼容 | `DASHSCOPE_API_KEY` |
| **Qwen** | OpenAI 兼容 | 自定义 base_url |
| **DeepSeek** | OpenAI 兼容 | 自定义 base_url |
| **OpenRouter** | OpenAI 兼容 | `OPENAI_API_KEY` + base_url |
| **MiniMax** | OpenAI 兼容 | 自定义 base_url |

---

## 技术栈

**后端：** Python 3.10+ • FastAPI • SQLite • MarkItDown • LangGraph

**前端：** React 18 • TypeScript • Vite • TailwindCSS • D3.js • i18n

**LLM：** Claude / Gemini / Qwen / DeepSeek / OpenRouter / OpenAI

**外部 API：** Semantic Scholar（论文元数据增强）

---

## 项目结构

```
meta-knowledge-graph/
├── backend/                  # FastAPI 后端
│   ├── main.py               # 应用入口、CORS、路由注册
│   ├── routes/               # API 路由处理器
│   ├── services/             # 业务逻辑服务
│   ├── schemas.py            # Pydantic 数据模型
│   └── dependencies.py       # 依赖注入
├── frontend/                 # React + TypeScript 前端
│   └── src/
│       ├── pages/            # 页面组件
│       ├── components/       # 共享组件 + 卡片
│       ├── i18n/             # 中英翻译
│       ├── lib/api/          # API 客户端模块
│       └── store/            # Zustand 状态管理
├── mkg/                      # 核心库
│   ├── database/             # SQLite 数据库包（核心、schema、迁移）
│   ├── repositories/         # 数据访问层
│   ├── agent/                # LangGraph 代理系统
│   │   ├── nodes/            # 代理节点
│   │   ├── tools.py          # 工具定义
│   │   └── research_graph.py # 深度研究编排
│   ├── dedup/                # 概念去重模块
│   ├── semantic_scholar.py   # S2 API 客户端
│   └── llm.py                # LLMClient + MKGChatModel 适配器（原生 HTTP）
├── scripts/                  # 工具脚本（演示数据生成）
├── docker/                   # Docker 配置
├── icon/                     # 项目图标
├── docs/                     # 演示截图和 GIF
└── Dockerfile                # 多阶段 Docker 构建
```

---

## API 参考

启动后端后访问 http://localhost:8089/docs 查看完整 API 文档。

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/papers/upload` | POST | 上传 PDF 文件 |
| `/api/papers/batch-upload` | POST | 批量上传 PDF |
| `/api/papers/batch-process` | POST | 批量处理论文 |
| `/api/concepts/` | GET | 获取所有概念 |
| `/api/concepts/{id}/research-points` | GET | 发现研究点 |
| `/api/concepts/{id}/search-papers` | GET | 按概念搜索论文 |
| `/api/concepts/dedup/scan` | POST | 扫描重复概念 |
| `/api/graph/export/obsidian/html` | GET | 导出交互式 HTML |
| `/api/agent/chat` | POST | 与 AI 代理对话 |
| `/api/agent/deep-research/start` | POST | 启动深度研究 |
| `/api/agent/deep-research/{id}/status` | GET | 查看研究进度 |

---

## 路线图

- [x] 两阶段概念提取
- [x] 研究点发现（4 种方法论）
- [x] 学术轻量主题 UI
- [x] 双语支持（中文/英文）
- [x] Semantic Scholar 元数据增强
- [x] 图谱搜索与筛选
- [x] 概念去重
- [x] 多格式导出
- [x] 批量处理
- [x] 多 LLM 后端
- [x] AI 研究代理（聊天、论文问答、引用分析、研究）
- [x] 异步深度研究 + 进度跟踪
- [x] 中文概念名自动翻译（LLM 驱动）
- [x] 研究点难度/新颖性/影响徽章
- [x] MarkItDown PDF 解析（无需 Java）
- [ ] 实时协作
- [ ] Neo4j 支持

---

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

---

<p align="center">
  <img src="icon/mkg-logo-horizontal.svg" alt="MKG Logo" width="200">
</p>

<p align="center">
  Made with ❤️ by <a href="https://github.com/Seaual">Seaual</a>
</p>
