# Meta Knowledge Graph

一个基于 LLM 的学术知识图谱引擎，支持从 PDF 论文自动提取概念层级结构，并以交互式力导向图可视化展示。

## 功能特性

- **PDF 论文解析** - 自动提取论文标题、作者、摘要等元数据
- **LLM 概念提取** - 使用 Claude/Gemini/Qwen 等大语言模型从论文中提取层次化概念结构
- **知识图谱可视化** - 类似 Obsidian/Neo4j 的力导向图交互式展示
- **研究点发现** - 基于知识图谱分析，发现潜在研究方向和创新点
- **中文概念支持** - 所有概念统一使用中文，便于知识关联

## 技术栈

### 后端
- Python 3.10+
- FastAPI - Web 框架
- SQLite - 数据存储
- PyMuPDF - PDF 解析
- Claude CLI / Anthropic API / Google AI / DashScope - LLM 接口

### 前端
- React 18
- TypeScript
- Vite
- TailwindCSS
- force-graph - Canvas 力导向图渲染
- d3-force - 物理引擎

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/meta-knowledge-graph.git
cd meta-knowledge-graph
```

### 2. 后端配置

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置 LLM

复制环境变量模板并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key（三选一）：

```env
# 方式一：Claude API（推荐）
ANTHROPIC_API_KEY=sk-ant-...

# 方式二：Google AI Studio
GOOGLE_API_KEY=...

# 方式三：阿里云 DashScope
DASHSCOPE_API_KEY=...
```

**或者**，如果你已安装 [Claude Code CLI](https://github.com/anthropics/claude-code)，系统会自动使用已配置的 API，无需额外配置。

### 4. 前端配置

```bash
cd frontend
npm install
```

### 5. 启动服务

```bash
# 启动后端（项目根目录）
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 启动前端（新终端，frontend 目录）
npm run dev
```

访问 http://localhost:5173 即可使用。

## 使用说明

### 上传论文

1. 进入「论文」页面
2. 点击上传按钮，选择 PDF 文件
3. 论文将出现在「待处理」列表中

### 处理论文

1. 在论文列表中点击「处理」按钮
2. 系统将调用 LLM 提取概念树
3. 处理完成后，概念将自动添加到知识图谱

### 浏览知识图谱

1. 进入「概念」页面
2. 力导向图展示所有概念及其层级关系
3. 拖拽节点调整位置，滚轮缩放
4. 使用左下角滑块调节节点斥力

### 发现研究点

1. 点击任意概念节点
2. 在右上角面板点击「发现研究点」
3. 系统将分析该概念的上游/下游/边缘节点
4. LLM 生成 3-5 个潜在研究方向

## 项目结构

```
meta-knowledge-graph/
├── backend/                 # FastAPI 后端
│   ├── main.py             # 应用入口
│   ├── routes/             # API 路由
│   │   ├── papers.py       # 论文相关 API
│   │   ├── concepts.py     # 概念相关 API
│   │   └── graph.py        # 图谱数据 API
│   └── schemas.py          # Pydantic 模型
├── frontend/                # React 前端
│   ├── src/
│   │   ├── pages/          # 页面组件
│   │   ├── lib/            # 工具库
│   │   └── App.tsx         # 应用入口
│   └── package.json
├── openclaw/                # 核心库
│   ├── database.py         # 数据库操作
│   ├── graph.py            # 图谱操作
│   └── pdf_parser.py       # PDF 解析 & LLM 提取
├── papers/                  # 论文存储
│   ├── pending/            # 待处理
│   └── processed/          # 已处理
└── openclaw.db              # SQLite 数据库
```

## API 文档

启动后端后访问 http://localhost:8000/docs 查看 Swagger API 文档。

### 主要接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/papers/` | GET | 获取所有论文 |
| `/api/papers/upload` | POST | 上传 PDF |
| `/api/papers/process` | POST | 处理论文提取概念 |
| `/api/concepts/` | GET | 获取所有概念 |
| `/api/concepts/{id}/research-points` | GET | 发现研究点 |
| `/api/graph/data` | GET | 获取图谱数据 |

## 概念层级定义

| 类别 | 英文 | 描述 | 示例 |
|------|------|------|------|
| 大领域 | field | 学科/领域 | 运筹学、人工智能 |
| 研究方向 | direction | 具体方向 | 车辆路径问题、强化学习 |
| 子方向 | subdirection | 细分方向 | 随机需求VRP、多智能体强化学习 |
| 任务 | task | 研究任务 | 应急配送、灾后救援 |
| 方法 | method | 方法/算法 | 模拟退火、分支切割算法 |
| 技术 | technique | 技术细节 | 值函数近似、梯度裁剪 |

## 开发计划

- [ ] 支持更多 LLM 后端（DeepSeek、OpenRouter 等）
- [ ] 概念合并与去重优化
- [ ] 导出为 Obsidian/Notion 格式
- [ ] 协作功能（多人编辑知识图谱）
- [ ] Neo4j 数据库支持

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License