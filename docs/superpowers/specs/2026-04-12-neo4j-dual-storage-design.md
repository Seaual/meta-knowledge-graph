# Neo4j 双存储同步 — 设计文档

**日期**: 2026-04-12
**状态**: 已批准

## 目标

将 Neo4j 作为概念图谱查询引擎集成到 MKG，与现有 SQLite 形成双存储架构。SQLite 保留为论文 CRUD/文件夹/配置的主存储，Neo4j 负责概念树、研究点发现、图谱导出的高效图查询。

## 架构

```
PDF → LLM 提取概念树 → 写入 SQLite (概念+关系)
                            ↓ 同步写入
                       Neo4j (Concept + HAS_SUB)

查询路由:
  概念树/研究点/图谱导出 → Neo4j (Cypher 原生图查询)
  论文 CRUD/文件夹/配置 → SQLite (保持现状)
```

## 数据模型映射

| SQLite 表 | Neo4j Label | 说明 |
|-----------|-------------|------|
| concepts (text, id, category, paper_count) | `Concept` | 概念节点，id 作为唯一属性 |
| concept_relations (parent_id, child_id, relation_type) | `:HAS_SUB` | 概念间父子关系 |

Neo4j 不存论文。论文-概念关联通过 `Concept.paper_count` 属性间接体现。

## 组件设计

### 1. mkg/neo4j_store.py（新文件）

替代现有 `neo4j_graph.py`。提供：
- `Neo4jStore` 类：连接管理、幂等写入、图查询
- 核心方法：`sync_concept()`, `sync_relation()`, `get_tree()`, `get_research_points()`, `get_stats()`
- 所有 Cypher 用 `MERGE`，重复写入不产生重复节点
- 环境变量：`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`

### 2. Repository 层同步

修改 `mkg/repositories/concept_repo.py` 的 `add()`, `add_relation()`, `update_paper_count()` 方法：
- 写入 SQLite 后同步到 Neo4j
- 环境变量 `USE_NEO4J=true` 控制是否启用
- Neo4j 未连接或写入失败时降级为 SQLite-only

### 3. API 路由集成

修改以下路由的概念查询走 Neo4j：
- `concepts_tree` 路由 → Neo4j 的 `get_tree()` 查询
- `concepts_research` 路由 → Neo4j 的图查询能力
- `graph export` 路由 → Neo4j 导出

其他路由（论文 CRUD、文件夹、配置）保持 SQLite。

### 4. CLI 增强

- `mkg neo4j status` — 显示连接状态 + 节点/关系统计
- `mkg neo4j sync` — 从 SQLite 全量同步到 Neo4j
- `mkg neo4j test` — 测试连接（已有）

## 错误处理

- Neo4j 连接失败：记录 warning 日志，继续用 SQLite
- 写入失败：幂等重试（最多 3 次），仍然失败则记录 error 不阻断主流程
- 读取失败（Neo4j 查询报错）：回退到 SQLite 查询

## 配置

```env
USE_NEO4J=true
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

## 工作量估算

约 3-5 天，分 4 个阶段：
1. Neo4jStore 实现（1-2 天）
2. Repository 层同步（0.5-1 天）
3. API 路由集成（1 天）
4. CLI + 测试（0.5-1 天）
