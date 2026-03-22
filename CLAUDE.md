# OpenClaw - 学术知识图谱引擎

核心工作流：PDF → LLM 概念提取 → SQLite/Neo4j 图谱 → Obsidian 导出

## 核心模块

| 模块 | 职责 |
|------|------|
| `cli.py` | CLI 入口 |
| `database.py` | SQLite 数据库（论文、概念、关系） |
| `pdf_parser.py` | PDF 解析 + LLM 概念提取 |
| `graph.py` | 知识图谱操作 |
| `neo4j_graph.py` | Neo4j 图数据库集成 |
| `obsidian_exporter.py` | Obsidian 导出 |

## LLM 配置

支持三种 API（三选一）：
- `ANTHROPIC_API_KEY` - Anthropic Claude
- `GOOGLE_API_KEY` - Google Gemini
- `DASHSCOPE_API_KEY` - DashScope/OpenAI 兼容

## 概念层级

- L0: 领域（人工智能、机器学习）
- L1: 方向（强化学习、计算机视觉）
- L2: 任务（多智能体、离线学习）
- L3: 方法（PPO、QMIX）
- L4: 细节（clip机制）

## 数据模型

```
papers (论文)
├── doi, title, abstract, authors, pdf_path

concepts (概念)
├── id, text, category, paper_count

concept_relations (概念层级)
├── parent_id, child_id

paper_concepts (论文-概念关联)
├── paper_doi, concept_id
```