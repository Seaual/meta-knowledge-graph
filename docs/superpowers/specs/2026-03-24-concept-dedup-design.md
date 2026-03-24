# 概念合并与去重优化设计

## 概述

为 meta-knowledge-graph 添加概念合并与去重功能，解决不同论文提取出重复概念的问题。

## 需求

- **问题**：不同论文提取出重复概念（如"强化学习" vs "强化学习方法"）
- **触发方式**：批量去重（手动触发命令/API）
- **判断策略**：让 LLM 判断是否应该合并
- **层级处理**：让 LLM 同时决定合并后的父子关系
- **执行方式**：人工确认后才执行

## 架构

```
用户触发去重
    ↓
按 category 分组
    ↓
组内生成候选对（文本相似度预筛选）
    ↓
LLM 批量判断：哪些应该合并 + 合并后的层级关系
    ↓
生成合并建议列表（供用户确认）
    ↓
用户确认后执行合并
```

## 核心模块

| 模块 | 职责 |
|------|------|
| `ConceptDeduplicator` | 去重控制器，协调整个流程 |
| `CandidateGenerator` | 候选对生成器，预筛选可能重复的概念对 |
| `MergeAnalyzer` | LLM 分析器，判断是否合并及合并后的层级关系 |
| `MergeExecutor` | 合并执行器，执行数据库操作 |

## 数据流程

### 第一步：候选对生成

```python
# 按 category 分组，组内生成候选对
candidates = []

for category in ['field', 'direction', 'method', 'technique']:
    concepts = db.get_concepts_by_category(category)

    for i, c1 in enumerate(concepts):
        for c2 in concepts[i+1:]:
            # 文本相似度预筛选（阈值 0.6）
            if text_similarity(c1.text, c2.text) >= 0.6:
                candidates.append((c1, c2))
```

### 第二步：LLM 分析

请求结构：

```json
{
  "candidates": [
    {"id": "rl", "text": "强化学习", "parents": ["机器学习"], "children": ["多智能体强化学习"]},
    {"id": "rl-method", "text": "强化学习方法", "parents": ["机器学习方法"], "children": []}
  ],
  "task": "判断哪些概念应该合并，以及合并后的层级关系"
}
```

响应结构：

```json
{
  "merge_suggestions": [
    {
      "source_id": "rl-method",
      "target_id": "rl",
      "confidence": 0.95,
      "rationale": "两者指向同一研究领域",
      "merged_relations": {
        "parents": ["机器学习"],
        "children": ["多智能体强化学习"]
      }
    }
  ]
}
```

### 第三步：用户确认

前端展示合并建议列表，用户可以：
- ✅ 接受
- ❌ 拒绝
- ✏️ 修改（选择保留哪个概念）

### 第四步：执行合并

```python
def execute_merge(source_id, target_id, merged_relations):
    # 1. 迁移论文关联
    db.migrate_paper_concepts(source_id, target_id)

    # 2. 更新父子关系
    db.update_concept_relations(target_id, merged_relations)

    # 3. 删除源概念
    db.delete_concept(source_id)
```

## API 设计

### POST /api/concepts/dedup/scan

触发去重扫描，返回候选合并建议列表。

请求：
```json
{}
```

响应：
```json
{
  "scan_id": "scan-20260324-001",
  "status": "completed",
  "candidates_found": 12,
  "merge_suggestions": [
    {
      "id": "merge-001",
      "source": {"id": "rl-method", "text": "强化学习方法", "paper_count": 3},
      "target": {"id": "rl", "text": "强化学习", "paper_count": 15},
      "confidence": 0.95,
      "rationale": "两者指向同一研究领域",
      "merged_relations": {
        "parents": ["机器学习"],
        "children": ["多智能体强化学习"]
      }
    }
  ]
}
```

### POST /api/concepts/dedup/execute

执行用户确认的合并操作。

请求：
```json
{
  "merge_ids": ["merge-001", "merge-003"]
}
```

响应：
```json
{
  "executed": 2,
  "details": [
    {"source": "rl-method", "target": "rl", "status": "success"},
    {"source": "dqn-alg", "target": "dqn", "status": "success"}
  ]
}
```

## LLM 配置

复用现有配置逻辑，优先使用 Claude CLI，回退到 API Key：

```python
def get_dedup_extractor():
    """获取去重用的 LLM 客户端"""
    # 优先使用 Claude CLI
    try:
        return ClaudeCLIClient()
    except:
        pass

    # 回退到 API Key
    if os.getenv("ANTHROPIC_API_KEY"):
        return AnthropicClient(os.getenv("ANTHROPIC_API_KEY"))
    elif os.getenv("GOOGLE_API_KEY"):
        return GoogleClient(os.getenv("GOOGLE_API_KEY"))
    elif os.getenv("DASHSCOPE_API_KEY"):
        return OpenAICompatibleClient(os.getenv("DASHSCOPE_API_KEY"))

    return None
```

## 文件结构

```
openclaw/
├── dedup/
│   ├── __init__.py
│   ├── deduplicator.py    # ConceptDeduplicator 主控制器
│   ├── candidate.py       # CandidateGenerator 候选对生成
│   ├── analyzer.py        # MergeAnalyzer LLM 分析
│   └── executor.py        # MergeExecutor 执行合并
├── database.py            # 新增合并相关方法
└── ...

backend/routes/
├── concepts.py            # 新增 dedup API 端点
└── ...
```

## 数据库新增方法

```python
# database.py 新增方法

def get_concepts_by_category(self, category: str) -> list:
    """按类别获取概念"""
    pass

def migrate_paper_concepts(self, source_id: str, target_id: str):
    """迁移论文关联：将 source 的论文关联迁移到 target"""
    pass

def update_concept_relations(self, concept_id: str, relations: dict):
    """更新概念的父子关系"""
    pass

def delete_concept(self, concept_id: str):
    """删除概念及其关联"""
    pass
```

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| LLM 未配置 | 返回 500 错误，提示用户配置 API Key |
| LLM 返回格式异常 | 解析失败的候选对跳过，记录日志，返回部分结果 |
| 概念不存在 | 执行合并时检查，返回 404 错误 |
| 合并冲突 | 确保论文关联正确迁移 |

## 边界情况

- **空库**：概念数量 < 2 时，直接返回空结果
- **超大库**：概念数量 > 500 时，分批处理（每批 50 个候选对）
- **循环依赖**：LLM 返回的层级关系需检测是否产生循环，若有则拒绝该建议

## 文本相似度算法

使用简单的字符级相似度计算：

```python
def text_similarity(text1: str, text2: str) -> float:
    """计算两个文本的相似度（0-1）"""
    # 使用编辑距离或 Jaccard 相似度
    # 阈值设为 0.6 用于预筛选
    pass
```

可以选择：
- `difflib.SequenceMatcher`（Python 内置）
- `Levenshtein` 距离
- 简单的字符集 Jaccard 相似度