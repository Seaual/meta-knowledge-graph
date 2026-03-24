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

for category in ['field', 'direction', 'subdirection', 'task', 'method', 'technique']:
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
    """执行合并操作（事务包装）"""
    try:
        # 开启事务
        cursor = self.conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        # 1. 迁移论文关联
        self.migrate_paper_concepts(source_id, target_id)

        # 2. 更新父子关系
        self.update_concept_relations(target_id, merged_relations)

        # 3. 删除源概念
        self.delete_concept(source_id)

        # 4. 重新计算受影响概念的 depth_cache
        self.recalculate_depth_cache(target_id)

        # 提交事务
        self.conn.commit()
    except Exception as e:
        self.conn.rollback()
        raise e
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

**注意**：所有 LLM 客户端都实现了 `extract_concepts(prompt)` 方法，去重功能使用该方法调用 LLM。

## 扫描结果存储

扫描结果使用内存缓存（Session 级别），不持久化到数据库：

```python
import threading
from datetime import datetime
import uuid

# 全局扫描结果缓存（线程安全）
_scan_results: Dict[str, dict] = {}
_scan_lock = threading.Lock()

def store_scan_result(scan_id: str, result: dict):
    """存储扫描结果"""
    with _scan_lock:
        _scan_results[scan_id] = {
            "result": result,
            "created_at": datetime.now()
        }

def get_scan_result(scan_id: str) -> Optional[dict]:
    """获取扫描结果"""
    with _scan_lock:
        entry = _scan_results.get(scan_id)
        if not entry:
            return None

        # 超过 1 小时过期
        if (datetime.now() - entry["created_at"]).seconds > 3600:
            del _scan_results[scan_id]
            return None

        return entry["result"]

def generate_scan_id() -> str:
    """生成扫描 ID"""
    return f"scan-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
```

**注意**：多 worker 部署时，每个 worker 有独立的内存缓存。如果需要跨 worker 共享，应使用 Redis 等外部缓存。

## 循环依赖检测

在执行合并前，使用 DFS 检测 LLM 返回的层级关系是否会产生循环：

```python
def detect_cycle(db, concept_id: str, new_parents: list, new_children: list) -> bool:
    """检测合并后的层级关系是否会产生循环

    Args:
        db: 数据库实例
        concept_id: 概念 ID
        new_parents: 新的父节点列表
        new_children: 新的子节点列表

    Returns:
        True 表示存在循环，False 表示无循环
    """
    # 构建临时图
    # 如果 concept_id 会成为自己的祖先或后代，则存在循环

    # 检查：新父节点是否是 concept_id 的后代？
    for parent_id in new_parents:
        if is_descendant(db, concept_id, parent_id):
            return True

    # 检查：新子节点是否是 concept_id 的祖先？
    for child_id in new_children:
        if is_ancestor(db, concept_id, child_id):
            return True

    return False

def is_descendant(db, ancestor_id: str, node_id: str) -> bool:
    """检查 node_id 是否是 ancestor_id 的后代"""
    visited = set()
    queue = [ancestor_id]

    while queue:
        current = queue.pop(0)
        if current == node_id:
            return True
        if current in visited:
            continue
        visited.add(current)

        children = db.get_concept_children(current)
        queue.extend([c['id'] for c in children])

    return False

def is_ancestor(db, descendant_id: str, node_id: str) -> bool:
    """检查 node_id 是否是 descendant_id 的祖先"""
    visited = set()
    queue = [descendant_id]

    while queue:
        current = queue.pop(0)
        if current == node_id:
            return True
        if current in visited:
            continue
        visited.add(current)

        parents = db.get_concept_parents(current)
        queue.extend([p['id'] for p in parents])

    return False
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
    """按类别获取概念

    Args:
        category: 概念类别 (field/direction/subdirection/task/method/technique)
    """
    cursor = self.conn.cursor()
    cursor.execute("""
        SELECT * FROM concepts WHERE category = ? ORDER BY paper_count DESC
    """, (category,))
    return [dict(row) for row in cursor.fetchall()]

def migrate_paper_concepts(self, source_id: str, target_id: str):
    """迁移论文关联：将 source 的论文关联迁移到 target"""
    cursor = self.conn.cursor()
    # 将 source 的论文关联迁移到 target（避免重复）
    cursor.execute("""
        INSERT OR IGNORE INTO paper_concepts (paper_doi, concept_id, confidence, source)
        SELECT paper_doi, ?, confidence, source
        FROM paper_concepts WHERE concept_id = ?
    """, (target_id, source_id))
    # 删除 source 的论文关联
    cursor.execute("""
        DELETE FROM paper_concepts WHERE concept_id = ?
    """, (source_id,))

    # 更新 target 的 paper_count
    cursor.execute("""
        UPDATE concepts SET paper_count = (
            SELECT COUNT(DISTINCT paper_doi) FROM paper_concepts WHERE concept_id = ?
        ) WHERE id = ?
    """, (target_id, target_id))

def update_concept_relations(self, concept_id: str, relations: dict):
    """更新概念的父子关系

    Args:
        concept_id: 概念 ID
        relations: {"parents": [...], "children": [...]}
    """
    cursor = self.conn.cursor()

    # 删除现有的父子关系
    cursor.execute("""
        DELETE FROM concept_relations WHERE parent_id = ? OR child_id = ?
    """, (concept_id, concept_id))

    # 添加新的父关系
    for parent_id in relations.get("parents", []):
        cursor.execute("""
            INSERT OR IGNORE INTO concept_relations (parent_id, child_id)
            VALUES (?, ?)
        """, (parent_id, concept_id))

    # 添加新的子关系
    for child_id in relations.get("children", []):
        cursor.execute("""
            INSERT OR IGNORE INTO concept_relations (parent_id, child_id)
            VALUES (?, ?)
        """, (concept_id, child_id))

def delete_concept(self, concept_id: str):
    """删除概念及其所有关联"""
    cursor = self.conn.cursor()

    # 删除论文关联
    cursor.execute("DELETE FROM paper_concepts WHERE concept_id = ?", (concept_id,))

    # 删除层级关系
    cursor.execute("""
        DELETE FROM concept_relations WHERE parent_id = ? OR child_id = ?
    """, (concept_id, concept_id))

    # 删除概念本身
    cursor.execute("DELETE FROM concepts WHERE id = ?", (concept_id,))

def recalculate_depth_cache(self, concept_id: str = None):
    """重新计算概念的深度缓存

    使用 BFS 从根节点开始计算所有概念的深度
    """
    cursor = self.conn.cursor()

    # 重置所有 depth_cache
    cursor.execute("UPDATE concepts SET depth_cache = -1")

    # 获取根概念（没有父节点的概念）
    cursor.execute("""
        SELECT id FROM concepts c
        LEFT JOIN concept_relations cr ON c.id = cr.child_id
        WHERE cr.parent_id IS NULL
    """)
    roots = [row['id'] for row in cursor.fetchall()]

    # BFS 计算深度
    from collections import deque
    queue = deque([(root_id, 0) for root_id in roots])

    while queue:
        node_id, depth = queue.popleft()

        # 更新深度
        cursor.execute("""
            UPDATE concepts SET depth_cache = ? WHERE id = ?
        """, (depth, node_id))

        # 获取子节点
        cursor.execute("""
            SELECT child_id FROM concept_relations WHERE parent_id = ?
        """, (node_id,))
        children = [row['child_id'] for row in cursor.fetchall()]

        for child_id in children:
            queue.append((child_id, depth + 1))
```

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| LLM 未配置 | 返回 500 错误，提示用户配置 API Key |
| LLM 返回格式异常 | 解析失败的候选对跳过，记录日志，返回部分结果 |
| 概念不存在 | 执行合并时检查，返回 404 错误 |
| 合并冲突 | 确保论文关联正确迁移 |
| 扫描结果过期 | scan_id 超过 1 小时后失效，需重新扫描 |
| 循环依赖 | 检测到循环时拒绝该合并建议，返回错误信息 |

## 安全考虑

去重 API 涉及数据修改操作，建议在生产环境中：

1. **访问控制**：限制 `/api/concepts/dedup/*` 端点的访问权限
2. **操作审计**：记录所有合并操作到日志
3. **数据备份**：执行前建议用户备份数据库

当前实现不包含认证机制，假设在可信环境中使用。如需生产部署，应在网关层添加认证。

## 边界情况

- **空库**：概念数量 < 2 时，直接返回空结果
- **超大库**：概念数量 > 500 时，分批处理（每批 50 个候选对）

```python
def generate_candidates_batch(concepts: list, batch_size: int = 50):
    """分批生成候选对"""
    candidates = []
    for i, c1 in enumerate(concepts):
        for c2 in concepts[i+1:]:
            if text_similarity(c1.text, c2.text) >= 0.6:
                candidates.append((c1, c2))

                # 达到批次大小，yield 一批
                if len(candidates) >= batch_size:
                    yield candidates
                    candidates = []

    # 返回剩余的候选对
    if candidates:
        yield candidates
```

- **循环依赖**：LLM 返回的层级关系需检测是否产生循环，若有则拒绝该建议

## 文本相似度算法

使用 Python 内置的 `difflib.SequenceMatcher`：

```python
from difflib import SequenceMatcher

def text_similarity(text1: str, text2: str) -> float:
    """计算两个文本的相似度（0-1）"""
    return SequenceMatcher(None, text1, text2).ratio()
```

阈值设为 0.6 用于预筛选。