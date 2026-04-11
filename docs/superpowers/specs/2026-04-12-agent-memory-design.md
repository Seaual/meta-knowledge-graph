# Agent Memory — 设计文档

**日期**: 2026-04-12
**状态**: 已批准

## 目标

为 MKG Agent 添加跨对话记忆和研究记忆库能力，让 Agent 在后续交互中自动使用用户偏好和历史发现，提升概念提取和研究推荐的智能化程度。

## 架构

```
mkg/memory.py
├── AgentMemory (统一入口)
│   ├── UserPreferences — 键值对用户偏好（研究方向、关注概念、常用类别）
│   ├── ConversationContext — 跨对话上下文（对话摘要、兴趣标签）
│   └── ResearchMemory — 结构化研究记忆（发现/方法/实验/洞察）
```

## 数据模型

### 1. user_preferences 表

| 字段 | 类型 | 说明 |
|------|------|------|
| key | TEXT PRIMARY KEY | 偏好键 |
| value | TEXT | JSON 值 |
| updated_at | TIMESTAMP | 自动更新时间 |

操作：`set(key, value)`, `get(key)`, `delete(key)`, `get_all()`

### 2. conversation_context 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | UUID |
| conv_id | TEXT | 关联的 conversation ID |
| summary | TEXT | 对话摘要 |
| key_concepts | TEXT | JSON 概念 ID 列表 |
| research_interests | TEXT | JSON 研究兴趣标签 |
| created_at | TIMESTAMP | 创建时间 |

操作：`summarize(conv_id, messages)`, `get(conv_id)`, `update_interests(conv_id, interests)`

### 3. research_memories 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | UUID |
| title | TEXT | 记忆标题 |
| content | TEXT | 内容详情 |
| memory_type | TEXT | discovery/method/experiment/insight |
| tags | TEXT | JSON 关键词标签 |
| concept_ids | TEXT | JSON 关联概念 ID |
| paper_doi | TEXT | 来源论文 DOI |
| source_section | TEXT | 来源论文章节 |
| created_at | TIMESTAMP | 创建时间 |

操作：`add()`, `search_by_tags()`, `search_by_concept()`, `search_by_type()`, `get_related()`, `delete()`

## 数据流

```
PDF 处理 → LLM 提取概念 → 写入 SQLite
                          ↓
                     LLM 生成研究记忆 → ResearchMemory.add()
                          ↓
               research_memories 表（带 tags + concept_ids）

用户对话 → conversation_repo 存储消息
                          ↓
               对话结束 → LLM 生成摘要 → ConversationContext.summarize()
                          ↓
               提取研究兴趣 → UserPreferences.update()

后续查询 → UserPreferences.get() → 过滤结果
              ResearchMemory.search() → 返回相关记忆
```

## 组件设计

### 1. mkg/memory.py（新文件）

统一入口 `AgentMemory` 类，内部管理三个子系统。

### 2. 集成点

- **PDF 处理流程**（`mkg process`）：概念提取后，LLM 同时生成研究记忆
- **API 路由**：`/api/memory/*` 提供偏好管理和记忆检索
- **CLI**：`mkg memory search/query/tags` 命令行检索

### 3. LLM 提示增强

调用 LLM 时自动注入相关记忆作为上下文（用户偏好 + 历史相关发现）。

## 错误处理

- LLM 生成记忆失败：记录 warning 日志，不阻断主流程
- 检索无结果：返回空列表，不抛异常
- 偏好不存在：返回 None 或默认值

## 测试

- `tests/test_memory.py` — 覆盖三个子系统的 CRUD 和检索
- 使用 `:memory:` SQLite，无需外部依赖
