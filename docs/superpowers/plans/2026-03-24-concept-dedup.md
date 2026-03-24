# 概念合并与去重优化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 meta-knowledge-graph 添加概念合并与去重功能，支持 LLM 判断重复概念并合并。

**Architecture:** 分层架构 - Database 层新增合并方法 → Dedup 模块处理去重逻辑 → API 层暴露接口。使用内存缓存存储扫描结果，LLM 判断合并决策。

**Tech Stack:** Python 3.10+, FastAPI, SQLite, difflib

---

## 文件结构

```
openclaw/
├── dedup/
│   ├── __init__.py          # 模块导出
│   ├── deduplicator.py      # 主控制器 + 扫描结果缓存
│   ├── candidate.py         # 候选对生成器
│   ├── analyzer.py          # LLM 分析器
│   └── executor.py          # 合并执行器 + 循环检测
├── database.py              # 新增 5 个方法
└── ...

backend/routes/
└── concepts.py              # 新增 2 个 API 端点
```

---

### Task 1: 数据库方法 - get_concepts_by_category

**Files:**
- Modify: `openclaw/database.py` (在 `get_all_concepts` 方法后添加)

- [ ] **Step 1: 编写方法实现**

在 `openclaw/database.py` 的 `get_all_concepts` 方法后添加：

```python
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
```

- [ ] **Step 2: 验证方法**

启动 Python 交互环境测试：

```bash
cd D:/meta-knowledge-graph-main
python -c "
from openclaw.database import Database
db = Database('openclaw.db')
db.connect()
print(db.get_concepts_by_category('field'))
db.close()
"
```

预期输出：返回 field 类别的概念列表（可能为空）

- [ ] **Step 3: 提交**

```bash
git add openclaw/database.py
git commit -m "feat(db): add get_concepts_by_category method"
```

---

### Task 2: 数据库方法 - merge 相关方法

**Files:**
- Modify: `openclaw/database.py` (在文件末尾 `__exit__` 方法前添加)

- [ ] **Step 1: 添加 migrate_paper_concepts 方法**

```python
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
```

- [ ] **Step 2: 添加 update_concept_relations 方法**

```python
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
```

- [ ] **Step 3: 添加 delete_concept 方法**

```python
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
```

- [ ] **Step 4: 添加 recalculate_depth_cache 方法**

```python
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

    self.conn.commit()
```

- [ ] **Step 5: 提交**

```bash
git add openclaw/database.py
git commit -m "feat(db): add merge-related database methods"
```

---

### Task 3: 创建 dedup 模块结构

**Files:**
- Create: `openclaw/dedup/__init__.py`
- Create: `openclaw/dedup/candidate.py`
- Create: `openclaw/dedup/analyzer.py`
- Create: `openclaw/dedup/executor.py`
- Create: `openclaw/dedup/deduplicator.py`

- [ ] **Step 1: 创建目录和 __init__.py**

```bash
mkdir -p D:/meta-knowledge-graph-main/openclaw/dedup
```

创建 `openclaw/dedup/__init__.py`：

```python
"""
概念去重模块

提供概念合并与去重功能：
- CandidateGenerator: 候选对生成器
- MergeAnalyzer: LLM 分析器
- MergeExecutor: 合并执行器
- ConceptDeduplicator: 主控制器
"""

from .candidate import CandidateGenerator
from .analyzer import MergeAnalyzer
from .executor import MergeExecutor
from .deduplicator import ConceptDeduplicator

__all__ = [
    'CandidateGenerator',
    'MergeAnalyzer',
    'MergeExecutor',
    'ConceptDeduplicator'
]
```

- [ ] **Step 2: 创建 candidate.py**

创建 `openclaw/dedup/candidate.py`：

```python
"""
候选对生成器 - 预筛选可能重复的概念对
"""

from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Generator
from dataclasses import dataclass


@dataclass
class ConceptPair:
    """概念对"""
    concept1: Dict
    concept2: Dict
    similarity: float


class CandidateGenerator:
    """候选对生成器"""

    # 相似度阈值
    SIMILARITY_THRESHOLD = 0.6

    # 需要处理的类别
    CATEGORIES = ['field', 'direction', 'subdirection', 'task', 'method', 'technique']

    def __init__(self, db):
        """
        初始化

        Args:
            db: Database 实例
        """
        self.db = db

    def text_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度（0-1）"""
        return SequenceMatcher(None, text1, text2).ratio()

    def generate_candidates(self) -> List[ConceptPair]:
        """生成所有候选对"""
        candidates = []

        for category in self.CATEGORIES:
            concepts = self.db.get_concepts_by_category(category)
            candidates.extend(self._generate_pairs_in_category(concepts))

        return candidates

    def generate_candidates_batch(self, batch_size: int = 50) -> Generator[List[ConceptPair], None, None]:
        """分批生成候选对（用于大库）"""
        batch = []

        for category in self.CATEGORIES:
            concepts = self.db.get_concepts_by_category(category)

            for i, c1 in enumerate(concepts):
                for c2 in concepts[i+1:]:
                    similarity = self.text_similarity(c1['text'], c2['text'])

                    if similarity >= self.SIMILARITY_THRESHOLD:
                        batch.append(ConceptPair(
                            concept1=c1,
                            concept2=c2,
                            similarity=similarity
                        ))

                        if len(batch) >= batch_size:
                            yield batch
                            batch = []

        if batch:
            yield batch

    def _generate_pairs_in_category(self, concepts: List[Dict]) -> List[ConceptPair]:
        """在同类概念中生成候选对"""
        pairs = []

        for i, c1 in enumerate(concepts):
            for c2 in concepts[i+1:]:
                similarity = self.text_similarity(c1['text'], c2['text'])

                if similarity >= self.SIMILARITY_THRESHOLD:
                    pairs.append(ConceptPair(
                        concept1=c1,
                        concept2=c2,
                        similarity=similarity
                    ))

        return pairs
```

- [ ] **Step 3: 创建 analyzer.py**

创建 `openclaw/dedup/analyzer.py`：

```python
"""
LLM 分析器 - 判断概念是否应该合并及合并后的层级关系
"""

import json
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class MergeSuggestion:
    """合并建议"""
    source_id: str
    target_id: str
    confidence: float
    rationale: str
    merged_relations: Dict[str, List[str]]


class MergeAnalyzer:
    """LLM 分析器"""

    def __init__(self, llm_client):
        """
        初始化

        Args:
            llm_client: LLM 客户端（需要有 extract_concepts 方法）
        """
        self.llm_client = llm_client

    def analyze(self, candidates: List) -> List[MergeSuggestion]:
        """
        分析候选对，返回合并建议

        Args:
            candidates: ConceptPair 列表

        Returns:
            MergeSuggestion 列表
        """
        if not candidates:
            return []

        # 构建 LLM prompt
        prompt = self._build_prompt(candidates)

        # 调用 LLM
        try:
            response = self.llm_client.extract_concepts(prompt)
            return self._parse_response(response, candidates)
        except Exception as e:
            print(f"LLM 分析失败: {e}")
            return []

    def _build_prompt(self, candidates: List) -> str:
        """构建 LLM prompt"""
        # 构建候选对信息
        candidate_info = []
        for i, pair in enumerate(candidates):
            # 获取父子关系
            c1_parents = self._get_parent_names(pair.concept1['id'])
            c1_children = self._get_child_names(pair.concept1['id'])
            c2_parents = self._get_parent_names(pair.concept2['id'])
            c2_children = self._get_child_names(pair.concept2['id'])

            candidate_info.append({
                "pair_id": i,
                "concept1": {
                    "id": pair.concept1['id'],
                    "text": pair.concept1['text'],
                    "paper_count": pair.concept1.get('paper_count', 0),
                    "parents": c1_parents,
                    "children": c1_children
                },
                "concept2": {
                    "id": pair.concept2['id'],
                    "text": pair.concept2['text'],
                    "paper_count": pair.concept2.get('paper_count', 0),
                    "parents": c2_parents,
                    "children": c2_children
                },
                "similarity": round(pair.similarity, 2)
            })

        prompt = f"""你是一个学术知识图谱维护助手。请分析以下概念对，判断哪些应该合并。

## 候选概念对

{json.dumps(candidate_info, ensure_ascii=False, indent=2)}

## 任务

对于每一对概念，判断它们是否应该合并。合并的判断标准：
1. 两个概念是否指向同一学术概念（只是名称略有不同）
2. 例如"强化学习"和"强化学习方法"应该合并
3. 但"强化学习"和"监督学习"不应该合并

## 输出格式

请输出 JSON 格式：

```json
{{
  "merge_suggestions": [
    {{
      "pair_id": 0,
      "should_merge": true,
      "target_id": "保留的概念ID（通常选择paper_count更高的）",
      "confidence": 0.95,
      "rationale": "简短说明为什么应该合并",
      "merged_parents": ["合并后的父概念ID列表"],
      "merged_children": ["合并后的子概念ID列表"]
    }},
    {{
      "pair_id": 1,
      "should_merge": false,
      "rationale": "简短说明为什么不应该合并"
    }}
  ]
}}
```

只输出 JSON，不要其他内容。对于不应该合并的概念对，should_merge 设为 false。
"""
        return prompt

    def _parse_response(self, response: str, candidates: List) -> List[MergeSuggestion]:
        """解析 LLM 响应"""
        import re

        suggestions = []

        try:
            # 尝试提取 JSON
            json_match = re.search(r'```json\s*(.+?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.strip()

            data = json.loads(json_str)

            for item in data.get('merge_suggestions', []):
                if not item.get('should_merge', False):
                    continue

                pair_id = item.get('pair_id')
                if pair_id is None or pair_id >= len(candidates):
                    continue

                pair = candidates[pair_id]

                suggestions.append(MergeSuggestion(
                    source_id=pair.concept2['id'] if item.get('target_id') == pair.concept1['id'] else pair.concept1['id'],
                    target_id=item.get('target_id', pair.concept1['id']),
                    confidence=item.get('confidence', 0.8),
                    rationale=item.get('rationale', ''),
                    merged_relations={
                        'parents': item.get('merged_parents', []),
                        'children': item.get('merged_children', [])
                    }
                ))

        except (json.JSONDecodeError, KeyError) as e:
            print(f"解析 LLM 响应失败: {e}")

        return suggestions

    def _get_parent_names(self, concept_id: str) -> List[str]:
        """获取父概念 ID 列表（需要从外部注入 db）"""
        # 这个方法在 deduplicator 中会被正确实现
        return []

    def _get_child_names(self, concept_id: str) -> List[str]:
        """获取子概念 ID 列表（需要从外部注入 db）"""
        return []
```

- [ ] **Step 4: 创建 executor.py**

创建 `openclaw/dedup/executor.py`：

```python
"""
合并执行器 - 执行概念合并操作
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class MergeResult:
    """合并结果"""
    source_id: str
    target_id: str
    status: str  # success / failed
    message: Optional[str] = None


class MergeExecutor:
    """合并执行器"""

    def __init__(self, db):
        """
        初始化

        Args:
            db: Database 实例
        """
        self.db = db

    def execute(self, source_id: str, target_id: str, merged_relations: Dict) -> MergeResult:
        """
        执行合并操作

        Args:
            source_id: 要合并的概念 ID（将被删除）
            target_id: 保留的概念 ID
            merged_relations: 合并后的层级关系 {"parents": [...], "children": [...]}

        Returns:
            MergeResult
        """
        try:
            # 1. 检查循环依赖
            if self._detect_cycle(target_id, merged_relations):
                return MergeResult(
                    source_id=source_id,
                    target_id=target_id,
                    status='failed',
                    message='检测到循环依赖，拒绝合并'
                )

            # 2. 开启事务执行合并
            cursor = self.db.conn.cursor()
            cursor.execute("BEGIN TRANSACTION")

            try:
                # 迁移论文关联
                self.db.migrate_paper_concepts(source_id, target_id)

                # 更新父子关系
                self.db.update_concept_relations(target_id, merged_relations)

                # 删除源概念
                self.db.delete_concept(source_id)

                # 重新计算深度缓存
                self.db.recalculate_depth_cache()

                self.db.conn.commit()

                return MergeResult(
                    source_id=source_id,
                    target_id=target_id,
                    status='success'
                )

            except Exception as e:
                self.db.conn.rollback()
                raise e

        except Exception as e:
            return MergeResult(
                source_id=source_id,
                target_id=target_id,
                status='failed',
                message=str(e)
            )

    def _detect_cycle(self, concept_id: str, merged_relations: Dict) -> bool:
        """检测合并后的层级关系是否会产生循环"""
        new_parents = merged_relations.get('parents', [])
        new_children = merged_relations.get('children', [])

        # 检查：新父节点是否是 concept_id 的后代？
        for parent_id in new_parents:
            if self._is_descendant(concept_id, parent_id):
                return True

        # 检查：新子节点是否是 concept_id 的祖先？
        for child_id in new_children:
            if self._is_ancestor(concept_id, child_id):
                return True

        return False

    def _is_descendant(self, ancestor_id: str, node_id: str) -> bool:
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

            children = self.db.get_concept_children(current)
            queue.extend([c['id'] for c in children])

        return False

    def _is_ancestor(self, descendant_id: str, node_id: str) -> bool:
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

            parents = self.db.get_concept_parents(current)
            queue.extend([p['id'] for p in parents])

        return False
```

- [ ] **Step 5: 创建 deduplicator.py**

创建 `openclaw/dedup/deduplicator.py`：

```python
"""
概念去重主控制器 - 协调整个去重流程
"""

import threading
from datetime import datetime
import uuid
from typing import Dict, Optional, List

from .candidate import CandidateGenerator, ConceptPair
from .analyzer import MergeAnalyzer, MergeSuggestion
from .executor import MergeExecutor, MergeResult


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


class ConceptDeduplicator:
    """概念去重主控制器"""

    def __init__(self, db, llm_client=None):
        """
        初始化

        Args:
            db: Database 实例
            llm_client: LLM 客户端（可选）
        """
        self.db = db
        self.llm_client = llm_client

        # 初始化子组件
        self.candidate_generator = CandidateGenerator(db)
        self.merge_executor = MergeExecutor(db)

        if llm_client:
            self.merge_analyzer = MergeAnalyzer(llm_client)
        else:
            self.merge_analyzer = None

    def scan(self) -> dict:
        """
        执行去重扫描

        Returns:
            {
                "scan_id": "...",
                "status": "completed",
                "candidates_found": N,
                "merge_suggestions": [...]
            }
        """
        scan_id = generate_scan_id()

        # 1. 生成候选对
        candidates = self.candidate_generator.generate_candidates()

        if not candidates:
            result = {
                "scan_id": scan_id,
                "status": "completed",
                "candidates_found": 0,
                "merge_suggestions": []
            }
            store_scan_result(scan_id, result)
            return result

        # 2. LLM 分析
        if not self.merge_analyzer:
            result = {
                "scan_id": scan_id,
                "status": "error",
                "error": "LLM not configured",
                "candidates_found": len(candidates),
                "merge_suggestions": []
            }
            store_scan_result(scan_id, result)
            return result

        # 为 analyzer 注入 db 以获取父子关系
        self.merge_analyzer._get_parent_names = lambda cid: [
            p['id'] for p in self.db.get_concept_parents(cid)
        ]
        self.merge_analyzer._get_child_names = lambda cid: [
            c['id'] for c in self.db.get_concept_children(cid)
        ]

        suggestions = self.merge_analyzer.analyze(candidates)

        # 3. 构建响应
        merge_suggestions = []
        for i, s in enumerate(suggestions):
            source = self.db.get_concept(s.source_id)
            target = self.db.get_concept(s.target_id)

            if not source or not target:
                continue

            merge_suggestions.append({
                "id": f"merge-{scan_id}-{i}",
                "source": {
                    "id": source['id'],
                    "text": source['text'],
                    "paper_count": source.get('paper_count', 0)
                },
                "target": {
                    "id": target['id'],
                    "text": target['text'],
                    "paper_count": target.get('paper_count', 0)
                },
                "confidence": s.confidence,
                "rationale": s.rationale,
                "merged_relations": s.merged_relations
            })

        result = {
            "scan_id": scan_id,
            "status": "completed",
            "candidates_found": len(candidates),
            "merge_suggestions": merge_suggestions
        }

        store_scan_result(scan_id, result)
        return result

    def execute_merge(self, scan_id: str, merge_ids: List[str]) -> dict:
        """
        执行合并操作

        Args:
            scan_id: 扫描 ID
            merge_ids: 要执行的合并建议 ID 列表

        Returns:
            {
                "executed": N,
                "details": [...]
            }
        """
        # 1. 获取扫描结果
        scan_result = get_scan_result(scan_id)
        if not scan_result:
            return {
                "executed": 0,
                "error": "Scan result not found or expired"
            }

        # 2. 找到对应的合并建议
        suggestions_map = {
            s['id']: s for s in scan_result.get('merge_suggestions', [])
        }

        # 3. 执行合并
        details = []
        executed = 0

        for merge_id in merge_ids:
            suggestion = suggestions_map.get(merge_id)
            if not suggestion:
                details.append({
                    "merge_id": merge_id,
                    "status": "failed",
                    "message": "Merge suggestion not found"
                })
                continue

            result = self.merge_executor.execute(
                source_id=suggestion['source']['id'],
                target_id=suggestion['target']['id'],
                merged_relations=suggestion['merged_relations']
            )

            details.append({
                "source": suggestion['source']['id'],
                "target": suggestion['target']['id'],
                "status": result.status,
                "message": result.message
            })

            if result.status == 'success':
                executed += 1

        return {
            "executed": executed,
            "details": details
        }
```

- [ ] **Step 6: 提交**

```bash
git add openclaw/dedup/
git commit -m "feat: add dedup module (candidate, analyzer, executor, deduplicator)"
```

---

### Task 4: API 端点 - scan

**Files:**
- Modify: `backend/routes/concepts.py`

- [ ] **Step 1: 添加导入和依赖**

在 `backend/routes/concepts.py` 文件顶部的导入部分添加：

```python
from openclaw.dedup import ConceptDeduplicator
```

在 `_extractor = None` 后添加：

```python
_deduplicator = None
```

- [ ] **Step 2: 添加 get_deduplicator 函数**

在 `get_extractor()` 函数后添加：

```python
def get_deduplicator():
    """获取去重器实例"""
    global _deduplicator
    if _deduplicator is None:
        extractor = get_extractor()
        _deduplicator = ConceptDeduplicator(get_db(), extractor.api_client if extractor else None)
    return _deduplicator
```

- [ ] **Step 3: 添加 scan 端点**

在文件末尾（最后一个路由后）添加：

```python
@router.post("/dedup/scan")
def dedup_scan():
    """
    触发去重扫描

    返回候选合并建议列表，需要用户确认后才执行合并
    """
    deduplicator = get_deduplicator()

    if not deduplicator.merge_analyzer:
        raise HTTPException(
            status_code=500,
            detail="LLM not configured. Please set ANTHROPIC_API_KEY, GOOGLE_API_KEY, or DASHSCOPE_API_KEY"
        )

    result = deduplicator.scan()
    return result
```

- [ ] **Step 4: 提交**

```bash
git add backend/routes/concepts.py
git commit -m "feat(api): add /api/concepts/dedup/scan endpoint"
```

---

### Task 5: API 端点 - execute

**Files:**
- Modify: `backend/routes/concepts.py`

- [ ] **Step 1: 添加请求模型**

在 `ResearchPointResponse` 类后添加：

```python
class DedupExecuteRequest(BaseModel):
    """去重执行请求"""
    scan_id: str
    merge_ids: List[str]
```

- [ ] **Step 2: 添加 execute 端点**

在 `dedup_scan` 端点后添加：

```python
@router.post("/dedup/execute")
def dedup_execute(request: DedupExecuteRequest):
    """
    执行合并操作

    用户确认后执行指定的合并建议
    """
    deduplicator = get_deduplicator()

    result = deduplicator.execute_merge(request.scan_id, request.merge_ids)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result
```

- [ ] **Step 3: 提交**

```bash
git add backend/routes/concepts.py
git commit -m "feat(api): add /api/concepts/dedup/execute endpoint"
```

---

### Task 6: 集成测试

**Files:**
- Test: API 端点测试

- [ ] **Step 1: 启动后端服务**

```bash
cd D:/meta-knowledge-graph-main
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 2: 测试 scan 端点**

在新终端中：

```bash
curl -X POST http://localhost:8000/api/concepts/dedup/scan -H "Content-Type: application/json"
```

预期输出：包含 `scan_id`、`status`、`merge_suggestions` 的 JSON

- [ ] **Step 3: 测试 execute 端点**

使用上一步返回的 `scan_id` 和 `merge_ids`：

```bash
curl -X POST http://localhost:8000/api/concepts/dedup/execute \
  -H "Content-Type: application/json" \
  -d '{"scan_id": "YOUR_SCAN_ID", "merge_ids": ["merge-xxx-0"]}'
```

预期输出：包含 `executed` 和 `details` 的 JSON

- [ ] **Step 4: 验证 Swagger 文档**

访问 http://localhost:8000/docs 确认新端点出现在 API 列表中

- [ ] **Step 5: 最终提交**

```bash
git add -A
git commit -m "feat: complete concept deduplication feature

- Add database methods for merge operations
- Add dedup module with candidate, analyzer, executor, deduplicator
- Add /api/concepts/dedup/scan and /execute endpoints
- Support LLM-based merge decision with user confirmation"
```

---

## 测试清单

- [ ] 数据库方法测试
  - `get_concepts_by_category` 返回正确类别的概念
  - `migrate_paper_concepts` 正确迁移论文关联
  - `update_concept_relations` 正确更新父子关系
  - `delete_concept` 完整删除概念及关联
  - `recalculate_depth_cache` 正确计算深度

- [ ] 去重模块测试
  - `CandidateGenerator` 正确生成候选对
  - `MergeAnalyzer` 正确解析 LLM 响应
  - `MergeExecutor` 正确执行合并
  - 循环依赖检测有效

- [ ] API 端点测试
  - `/dedup/scan` 返回有效结果
  - `/dedup/execute` 正确执行合并
  - 错误情况正确处理（LLM 未配置、scan_id 过期等）

---

## 注意事项

1. **LLM 配置**：确保环境变量中配置了 `ANTHROPIC_API_KEY`、`GOOGLE_API_KEY` 或 `DASHSCOPE_API_KEY`

2. **数据备份**：执行合并前建议备份数据库

3. **大库处理**：概念数量 > 500 时考虑使用 `generate_candidates_batch` 分批处理