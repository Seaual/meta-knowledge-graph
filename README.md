# OpenClaw

学术知识图谱引擎：PDF → LLM 概念提取 → SQLite/Neo4j 图谱 → Obsidian 导出

## 核心流程

```
PDF 论文 ──→ LLM 概念提取 ──→ SQLite/Neo4j ──→ Obsidian
```

## 安装

```bash
pip install -r requirements.txt
```

## 配置

创建 `.env` 文件，配置 LLM API（三选一）：

```bash
# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-xxx

# Google Gemini
GOOGLE_API_KEY=xxx

# DashScope/OpenAI 兼容
DASHSCOPE_API_KEY=xxx
```

Neo4j 配置（可选）：

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

## 使用

```bash
# 初始化数据库
python -m openclaw init

# 处理单篇论文
python -m openclaw process paper.pdf

# 批量处理
python -m openclaw batch ./papers

# 查看图谱
python -m openclaw tree
python -m openclaw ls
python -m openclaw search "机器学习"

# 导出到 Obsidian
python -m openclaw export ./obsidian_vault

# 从 Neo4j 导出
python -m openclaw export ./vault --neo4j
```

## 命令

| 命令 | 说明 |
|------|------|
| `init` | 初始化数据库 |
| `process <pdf>` | 处理单篇 PDF |
| `batch <folder>` | 批量处理文件夹 |
| `tree` | 查看知识图谱树 |
| `ls [concept]` | 列出概念 |
| `cd <concept>` | 导航到概念 |
| `search <query>` | 搜索概念 |
| `stats` | 统计信息 |
| `export <vault>` | 导出到 Obsidian |
| `neo4j-test` | 测试 Neo4j 连接 |
| `neo4j-migrate` | 迁移到 Neo4j |

## 目录结构

```
openclaw/
├── cli.py           # CLI 入口
├── database.py      # SQLite 数据库
├── pdf_parser.py    # PDF 解析 + LLM 提取
├── graph.py         # 知识图谱操作
├── neo4j_graph.py   # Neo4j 集成
└── obsidian_exporter.py  # Obsidian 导出
```

## 概念层级

LLM 自动提取概念并分层：

| 层级 | 类型 | 示例 |
|------|------|------|
| L0 | 领域 | 人工智能、机器学习 |
| L1 | 方向 | 强化学习、计算机视觉 |
| L2 | 任务 | 多智能体、离线学习 |
| L3 | 方法 | PPO、QMIX、BERT |
| L4 | 细节 | clip机制、注意力头 |

## 后续计划

- [ ] Web 界面
- [ ] 可视化图谱
- [ ] RAG 问答