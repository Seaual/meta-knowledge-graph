# Neo4j 双存储同步 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Neo4j 作为概念图谱查询引擎集成到 MKG，与 SQLite 形成双存储架构。论文处理时概念自动同步到 Neo4j，概念树/研究点/图谱查询走 Neo4j。

**Architecture:** 新建 `mkg/neo4j_store.py` 替代旧的 `mkg/neo4j_graph.py`。ConceptRepository 写入时同步到 Neo4j。API 路由的概念树/研究点/图谱导出改为从 Neo4j 读取。Neo4j 失败时自动降级为 SQLite。

**Tech Stack:** neo4j driver, FastAPI, SQLite, Cypher, pytest

---

## 文件映射

| 文件 | 类型 | 职责 |
|------|------|------|
| `mkg/neo4j_store.py` | 新建 | Neo4j 存储层，提供概念同步和图查询 |
| `mkg/repositories/concept_repo.py` | 修改 | 在 add/add_relation 中同步到 Neo4j |
| `mkg/database.py` | 修改 | 添加 `_neo4j_store` 属性 |
| `backend/services/concept_service.py` | 修改 | get_tree/get_children/get_parents 优先走 Neo4j |
| `backend/services/research_service.py` | 修改 | discover_research_points 优先走 Neo4j |
| `backend/routes/graph.py` | 修改 | get_graph_data/tree-data 优先走 Neo4j |
| `mkg/cli.py` | 修改 | 增强 neo4j 命令 |
| `tests/test_neo4j_store.py` | 新建 | Neo4jStore 单元测试（mock driver） |
| `tests/test_concept_repo_sync.py` | 新建 | Repository 同步行为测试 |
| `.env.example` | 修改 | 添加 USE_NEO4J 配置 |

---

### Task 1: Neo4jStore 核心实现

**Files:**
- Create: `mkg/neo4j_store.py`

- [ ] **Step 1: Write Neo4jStore class skeleton**

Create `mkg/neo4j_store.py`:

```python
"""
Neo4j 概念图谱存储层

与 SQLite 形成双存储架构：
- SQLite: 论文 CRUD、文件夹、配置的主存储
- Neo4j: 概念树、研究点发现、图谱导出的图查询引擎
"""

import os
import logging

logger = logging.getLogger(__name__)


class Neo4jStore:
    """Neo4j 概念图谱存储"""

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.driver = None
        self.connected = False

        if uri is None:
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        if user is None:
            user = os.getenv("NEO4J_USER", "neo4j")
        if password is None:
            password = os.getenv("NEO4J_PASSWORD", "password")

        try:
            from neo4j import GraphDatabase

            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            with self.driver.session() as session:
                session.run("RETURN 1")
            self.connected = True
            self._init_schema()
            logger.info("Neo4j connected")
        except ImportError:
            logger.warning("neo4j package not installed")
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e}")

    def _init_schema(self):
        """创建索引和约束"""
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS concept_id_unique FOR (c:Concept) REQUIRE c.id IS UNIQUE")
            session.run("CREATE INDEX IF NOT EXISTS concept_text_idx FOR (c:Concept) ON (c.text)")
            session.run("CREATE INDEX IF NOT EXISTS concept_category_idx FOR (c:Concept) ON (c.category)")

    def close(self):
        if self.driver:
            self.driver.close()
            self.connected = False

    def sync_concept(self, concept_data: dict) -> bool:
        """
        同步单个概念到 Neo4j（幂等）

        Args:
            concept_data: {id, text, text_en, text_zh, category, paper_count}

        Returns:
            True if synced, False if not connected
        """
        if not self.connected:
            return False
        try:
            with self.driver.session() as session:
                session.run("""
                    MERGE (c:Concept {id: $id})
                    SET c.text = $text,
                        c.text_en = coalesce($text_en, c.text_en),
                        c.text_zh = coalesce($text_zh, c.text_zh),
                        c.category = $category,
                        c.paper_count = coalesce($paper_count, 0),
                        c.updated_at = datetime()
                """, {
                    'id': concept_data.get('id'),
                    'text': concept_data.get('text', ''),
                    'text_en': concept_data.get('text_en'),
                    'text_zh': concept_data.get('text_zh'),
                    'category': concept_data.get('category'),
                    'paper_count': concept_data.get('paper_count', 0),
                })
            return True
        except Exception as e:
            logger.error(f"Failed to sync concept: {e}")
            return False

    def sync_relation(self, parent_id: str, child_id: str,
                      relation_type: str = "parent-child") -> bool:
        """
        同步概念层级关系到 Neo4j（幂等）

        Args:
            parent_id: 父概念 ID
            child_id: 子概念 ID
            relation_type: 关系类型

        Returns:
            True if synced, False if not connected
        """
        if not self.connected:
            return False
        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (parent:Concept {id: $parent_id})
                    MATCH (child:Concept {id: $child_id})
                    MERGE (parent)-[r:HAS_SUB]->(child)
                    SET r.relation_type = $relation_type
                """, {
                    'parent_id': parent_id,
                    'child_id': child_id,
                    'relation_type': relation_type,
                })
            return True
        except Exception as e:
            logger.error(f"Failed to sync relation: {e}")
            return False

    def get_tree(self, root_id: str = None, max_depth: int = 10) -> dict:
        """
        从 Neo4j 获取概念树

        Args:
            root_id: 根概念 ID（可选，默认取第一个根概念）
            max_depth: 最大深度

        Returns:
            概念树字典
        """
        if not self.connected:
            return {}
        try:
            with self.driver.session() as session:
                if root_id is None:
                    result = session.run("""
                        MATCH (c:Concept)
                        WHERE NOT EXISTS { (c)<-[:HAS_SUB]-() }
                        RETURN c.id as id, c.text as text, c.category as category,
                               c.paper_count as paper_count
                        ORDER BY c.paper_count DESC LIMIT 1
                    """)
                    record = result.single()
                    if not record:
                        return {}
                    root_id = record['id']

                return self._build_tree(session, root_id, 0, max_depth)
        except Exception as e:
            logger.error(f"Failed to get tree from Neo4j: {e}")
            return {}

    def _build_tree(self, session, concept_id: str, depth: int, max_depth: int) -> dict:
        """递归构建概念树"""
        if depth > max_depth:
            return {'id': concept_id, 'truncated': True}

        result = session.run("""
            MATCH (c:Concept {id: $id})
            RETURN c.id as id, c.text as text, c.text_en as text_en,
                   c.text_zh as text_zh, c.category as category,
                   c.paper_count as paper_count
        """, {'id': concept_id})
        record = result.single()
        if not record:
            return {}

        node = dict(record)

        children_result = session.run("""
            MATCH (parent:Concept {id: $id})-[:HAS_SUB]->(child:Concept)
            RETURN child.id as id, child.text as text, child.category as category,
                   child.paper_count as paper_count
            ORDER BY child.paper_count DESC
        """, {'id': concept_id})

        node['children'] = []
        for child in children_result:
            child_node = self._build_tree(session, child['id'], depth + 1, max_depth)
            if child_node:
                node['children'].append(child_node)

        return node

    def get_children(self, concept_id: str) -> list[dict]:
        """获取子概念列表"""
        if not self.connected:
            return []
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (parent:Concept {id: $id})-[:HAS_SUB]->(child:Concept)
                    RETURN child.id as id, child.text as text, child.text_en as text_en,
                           child.text_zh as text_zh, child.category as category,
                           child.paper_count as paper_count
                    ORDER BY child.paper_count DESC
                """, {'id': concept_id})
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"Failed to get children from Neo4j: {e}")
            return []

    def get_parents(self, concept_id: str) -> list[dict]:
        """获取父概念列表"""
        if not self.connected:
            return []
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (child:Concept {id: $id})<-[:HAS_SUB]-(parent:Concept)
                    RETURN parent.id as id, parent.text as text, parent.text_en as text_en,
                           parent.text_zh as text_zh, parent.category as category,
                           parent.paper_count as paper_count
                """, {'id': concept_id})
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"Failed to get parents from Neo4j: {e}")
            return []

    def get_root_concepts(self) -> list[dict]:
        """获取根概念（没有父节点的概念）"""
        if not self.connected:
            return []
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (c:Concept)
                    WHERE NOT EXISTS { (c)<-[:HAS_SUB]-() }
                    RETURN c.id as id, c.text as text, c.category as category,
                           c.paper_count as paper_count
                    ORDER BY c.paper_count DESC
                """)
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"Failed to get roots from Neo4j: {e}")
            return []

    def get_all_concepts(self) -> list[dict]:
        """获取所有概念"""
        if not self.connected:
            return []
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (c:Concept)
                    RETURN c.id as id, c.text as text, c.text_en as text_en,
                           c.text_zh as text_zh, c.category as category,
                           c.paper_count as paper_count
                    ORDER BY c.paper_count DESC
                """)
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"Failed to get all concepts from Neo4j: {e}")
            return []

    def get_graph_data(self, max_depth: int = 3) -> dict:
        """
        获取图谱数据（nodes + edges），用于前端 D3 可视化

        Returns:
            {'nodes': [...], 'edges': [...]}
        """
        if not self.connected:
            return {'nodes': [], 'edges': []}
        try:
            with self.driver.session() as session:
                nodes_result = session.run("""
                    MATCH (c:Concept)
                    RETURN c.id as id, c.text as label, c.text_en as label_en,
                           c.category as category, c.paper_count as paper_count
                """)
                nodes = [dict(r) for r in nodes_result]

                edges_result = session.run("""
                    MATCH (parent:Concept)-[r:HAS_SUB]->(child:Concept)
                    RETURN parent.id as source, child.id as target
                """)
                edges = [dict(r) for r in edges_result]

                return {'nodes': nodes, 'edges': edges}
        except Exception as e:
            logger.error(f"Failed to get graph data from Neo4j: {e}")
            return {'nodes': [], 'edges': []}

    def sync_all_from_sqlite(self, db) -> dict:
        """
        从 SQLite 全量同步到 Neo4j

        Args:
            db: Database 实例

        Returns:
            {'concepts_synced': N, 'relations_synced': M}
        """
        if not self.connected:
            return {'concepts_synced': 0, 'relations_synced': 0, 'error': 'Not connected'}

        count = 0
        concepts = db.concepts.get_all()
        for concept in concepts:
            self.sync_concept(concept)
            count += 1

        rel_count = 0
        cursor = db.conn.execute("SELECT parent_id, child_id, relation_type FROM concept_relations")
        for row in cursor.fetchall():
            self.sync_relation(row['parent_id'], row['child_id'], row['relation_type'])
            rel_count += 1

        return {'concepts_synced': count, 'relations_synced': rel_count}

    def get_stats(self) -> dict:
        """获取 Neo4j 图谱统计"""
        if not self.connected:
            return {}
        try:
            with self.driver.session() as session:
                total = session.run("MATCH (c:Concept) RETURN count(c) as count").single()['count']
                relations = session.run("MATCH ()-[r:HAS_SUB]->() RETURN count(r) as count").single()['count']
                roots = session.run("""
                    MATCH (c:Concept)
                    WHERE NOT EXISTS { (c)<-[:HAS_SUB]-() }
                    RETURN count(c) as count
                """).single()['count']
                return {
                    'total_concepts': total,
                    'total_relations': relations,
                    'root_concepts': roots,
                }
        except Exception as e:
            logger.error(f"Failed to get stats from Neo4j: {e}")
            return {}

    def update_paper_count(self, concept_id: str, count: int) -> bool:
        """更新概念的论文计数"""
        if not self.connected:
            return False
        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (c:Concept {id: $id})
                    SET c.paper_count = $count
                """, {'id': concept_id, 'count': count})
            return True
        except Exception as e:
            logger.error(f"Failed to update paper count: {e}")
            return False

    def search_concepts(self, query: str, limit: int = 20) -> list[dict]:
        """搜索概念"""
        if not self.connected:
            return []
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (c:Concept)
                    WHERE c.text CONTAINS $query
                       OR c.text_en CONTAINS $query
                       OR c.text_zh CONTAINS $query
                    RETURN c.id as id, c.text as text, c.category as category,
                           c.paper_count as paper_count
                    ORDER BY c.paper_count DESC
                    LIMIT $limit
                """, {'query': query, 'limit': limit})
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"Failed to search concepts from Neo4j: {e}")
            return []
```

- [ ] **Step 2: Commit**

```bash
git add mkg/neo4j_store.py
git commit -m "feat: add Neo4jStore for concept graph sync and querying"
```

---

### Task 2: Repository 层同步

**Files:**
- Modify: `mkg/repositories/concept_repo.py`
- Modify: `mkg/database.py`
- Test: `tests/test_concept_repo_sync.py`

- [ ] **Step 1: 修改 `mkg/database.py` 添加 Neo4jStore 属性**

在 `mkg/database.py` 的 `Database` 类中，添加 `_neo4j_store` 属性和 `neo4j_store` property：

```python
# 在 __init__ 方法中，在 self._research = None 之后添加:
self._neo4j_store = None

# 在 close 方法中，在 if self.conn: 之前添加:
if self._neo4j_store:
    self._neo4j_store.close()
    self._neo4j_store = None

# 添加 property:
@property
def neo4j_store(self) -> 'Neo4jStore | None':
    """获取 Neo4j 存储（延迟初始化，如果启用）"""
    if self._neo4j_store is None:
        import os
        if os.getenv("USE_NEO4J", "").lower() in ("true", "1", "yes"):
            from .neo4j_store import Neo4jStore
            self._neo4j_store = Neo4jStore()
    return self._neo4j_store
```

- [ ] **Step 2: 修改 `mkg/repositories/concept_repo.py` 的 `add()` 方法**

在 `add()` 方法的 `return concept_id` 之前，添加 Neo4j 同步调用：

在 `add()` 方法中，找到最后的 `return concept_id` 行，在它之前添加同步代码。实际修改后的 `add()` 末尾应该像这样：

```python
        # ... [前面所有现有代码保持不变] ...

        # 同步到 Neo4j
        if self._db.neo4j_store:
            self._db.neo4j_store.sync_concept(concept_data)

        return concept_id
```

注意：只需在 `return concept_id` 之前添加那 3 行 if 块，不要修改方法的其他部分。

- [ ] **Step 3: 修改 `mkg/repositories/concept_repo.py` 的 `add_relation()` 方法**

在 `add_relation()` 的 `execute_write(...)` 之后添加：

```python
def add_relation(self, parent_id: str, child_id: str,
                 relation_type: str = "parent-child"):
    internal_type = 'is_subconcept_of' if relation_type == 'parent-child' else relation_type
    self.execute_write("""
        INSERT OR REPLACE INTO concept_relations (parent_id, child_id, relation_type)
        VALUES (?, ?, ?)
    """, (parent_id, child_id, internal_type))

    # 同步到 Neo4j
    if self._db.neo4j_store:
        self._db.neo4j_store.sync_relation(parent_id, child_id, relation_type)
```

- [ ] **Step 4: 修改 `mkg/repositories/concept_repo.py` 的 `_update_paper_count()` 方法**

在 `_update_paper_count()` 的 `execute_write(...)` 之后添加：

```python
def _update_paper_count(self, concept_id: str) -> None:
    self.execute_write("""
        UPDATE concepts SET paper_count = (
            SELECT COUNT(DISTINCT paper_doi) FROM paper_concepts WHERE concept_id = ?
        ) WHERE id = ?
    """, (concept_id, concept_id))

    # 同步到 Neo4j
    if self._db.neo4j_store:
        count = self.execute_read(
            "SELECT COUNT(DISTINCT paper_doi) as count FROM paper_concepts WHERE concept_id = ?",
            (concept_id,)
        ).fetchone()['count']
        self._db.neo4j_store.update_paper_count(concept_id, count)
```

- [ ] **Step 5: 创建 `tests/test_concept_repo_sync.py`**

测试 Neo4j 同步行为（mock Neo4jStore）：

```python
"""
ConceptRepository Neo4j 同步行为测试
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from mkg.database import Database
from mkg.repositories.concept_repo import ConceptRepository


@pytest.fixture
def test_db():
    db = Database(":memory:")
    db.connect()
    yield db
    db.close()


@pytest.fixture
def concept_repo(test_db):
    return ConceptRepository(test_db)


def test_add_concept_calls_neo4j_sync(concept_repo, test_db):
    """添加概念时应调用 Neo4jStore.sync_concept"""
    mock_store = MagicMock()
    test_db._neo4j_store = mock_store

    concept_repo.add({"id": "test-concept", "text": "Test Concept", "category": "field"})

    mock_store.sync_concept.assert_called_once()
    call_args = mock_store.sync_concept.call_args[0][0]
    assert call_args["id"] == "test-concept"
    assert call_args["text"] == "Test Concept"


def test_add_relation_calls_neo4j_sync(concept_repo, test_db):
    """添加关系时应调用 Neo4jStore.sync_relation"""
    mock_store = MagicMock()
    test_db._neo4j_store = mock_store

    # 先添加两个概念
    concept_repo.add({"id": "parent", "text": "Parent", "category": "field"})
    concept_repo.add({"id": "child", "text": "Child", "category": "direction"})

    concept_repo.add_relation("parent", "child")

    mock_store.sync_relation.assert_called_once_with("parent", "child", "parent-child")


def test_no_neo4j_when_disabled(concept_repo, test_db):
    """Neo4j 未连接时不影响 SQLite 写入"""
    test_db._neo4j_store = None

    concept_repo.add({"id": "solo", "text": "Solo Concept", "category": "method"})

    result = concept_repo.get("solo")
    assert result is not None
    assert result["text"] == "Solo Concept"
```

- [ ] **Step 6: 运行测试**

```bash
pytest tests/test_concept_repo_sync.py -v
```

Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
git add mkg/database.py mkg/repositories/concept_repo.py tests/test_concept_repo_sync.py
git commit -m "feat: sync concept writes from SQLite to Neo4j"
```

---

### Task 3: API 路由集成 — 概念树/研究点/图谱

**Files:**
- Modify: `backend/services/concept_service.py`
- Modify: `backend/services/research_service.py`
- Modify: `backend/routes/graph.py`

- [ ] **Step 1: 修改 `backend/services/concept_service.py`**

修改 `get_tree`, `get_children`, `get_parents`, `get_roots` 方法，优先从 Neo4j 读取，失败时回退到 SQLite：

```python
# backend/services/concept_service.py

class ConceptService:
    """概念数据访问服务"""

    def __init__(self, db: Database):
        self.db = db

    def list(self) -> list[dict]:
        return self.db.concepts.get_all()

    def get(self, concept_id: str) -> dict | None:
        concept = self.db.concepts.get(concept_id)
        if concept:
            concept['children'] = self.get_children(concept_id)
            concept['parents'] = self.get_parents(concept_id)
        return concept

    def search(self, query: str) -> list[dict]:
        neo4j = self.db.neo4j_store
        if neo4j and neo4j.connected:
            results = neo4j.search_concepts(query)
            if results:
                return results
        # fallback to SQLite
        cursor = self.db.execute_read(
            "SELECT * FROM concepts WHERE text LIKE ? ORDER BY paper_count DESC LIMIT 50",
            (f"%{query}%",)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_roots(self) -> list[dict]:
        neo4j = self.db.neo4j_store
        if neo4j and neo4j.connected:
            results = neo4j.get_root_concepts()
            if results is not None:
                return results
        return self.db.concepts.get_root()

    def get_tree(self, root_id: str = None) -> dict:
        neo4j = self.db.neo4j_store
        if neo4j and neo4j.connected:
            tree = neo4j.get_tree(root_id)
            if tree:
                return tree
        return self.db.concepts.get_tree(root_id)

    def get_children(self, concept_id: str) -> list[dict]:
        neo4j = self.db.neo4j_store
        if neo4j and neo4j.connected:
            results = neo4j.get_children(concept_id)
            if results is not None:
                return results
        return self.db.concepts.get_children(concept_id)

    def get_parents(self, concept_id: str) -> list[dict]:
        neo4j = self.db.neo4j_store
        if neo4j and neo4j.connected:
            results = neo4j.get_parents(concept_id)
            if results is not None:
                return results
        return self.db.concepts.get_parents(concept_id)

    def get_papers(self, concept_id: str, limit: int = 20) -> list[dict]:
        papers = self.db.concepts.get_papers(concept_id)
        return papers[:limit]
```

- [ ] **Step 2: 修改 `backend/services/research_service.py`**

在 `discover_research_points` 方法中，获取 children/parents 时优先走 Neo4j：

在类中添加一个 helper 方法：

```python
def _get_children(self, concept_id: str) -> list[dict]:
    """获取子概念，优先 Neo4j"""
    neo4j = self.db.neo4j_store
    if neo4j and neo4j.connected:
        results = neo4j.get_children(concept_id)
        if results is not None:
            return results
    return self.db.concepts.get_children(concept_id)

def _get_parents(self, concept_id: str) -> list[dict]:
    """获取父概念，优先 Neo4j"""
    neo4j = self.db.neo4j_store
    if neo4j and neo4j.connected:
        results = neo4j.get_parents(concept_id)
        if results is not None:
            return results
    return self.db.concepts.get_parents(concept_id)
```

然后修改 `discover_research_points` 中的调用：

```python
# 将:
children = self.db.concepts.get_children(concept_id)
parents = self.db.concepts.get_parents(concept_id)
# 改为:
children = self._get_children(concept_id)
parents = self._get_parents(concept_id)
```

- [ ] **Step 3: 修改 `backend/routes/graph.py`**

修改 `get_graph_data` 和 `get_tree_data`，优先从 Neo4j 获取数据：

在文件顶部添加导入：

```python
import os
```

修改 `get_graph_data` 函数，在获取 concepts 之前添加：

```python
@router.get("/data", response_model=GraphData)
def get_graph_data(max_depth: int = 3, folder: str = None):
    db = get_db()

    # 如果未指定文件夹且 Neo4j 已连接，直接从 Neo4j 获取
    if not folder:
        neo4j = db.neo4j_store
        if neo4j and neo4j.connected:
            graph_data = neo4j.get_graph_data()
            nodes = [
                GraphNode(
                    id=n['id'],
                    label=n['label'],
                    label_en=n.get('label_en'),
                    category=n.get('category', 'method'),
                    paper_count=n.get('paper_count', 0)
                )
                for n in graph_data['nodes']
            ]
            edges = [
                GraphEdge(source=e['source'], target=e['target'], type="parent-child")
                for e in graph_data['edges']
            ]
            return GraphData(nodes=nodes, edges=edges)

    # fallback to SQLite
    graph = get_graph()
    # fallback to SQLite — full existing function:
    graph = get_graph()

    nodes = []
    edges = []

    if folder:
        concepts = db.get_concepts_by_folder(folder)
    else:
        concepts = db.get_all_concepts()
    concept_map = {c['id']: c for c in concepts}

    for concept in concepts:
        nodes.append(GraphNode(
            id=concept['id'],
            label=concept['text'],
            label_en=concept.get('text_en'),
            category=concept.get('category', 'method'),
            paper_count=concept.get('paper_count', 0)
        ))

    if folder:
        relations = db.get_concept_relations_by_folder(folder)
        for row in relations:
            if row['parent_id'] in concept_map and row['child_id'] in concept_map:
                edges.append(GraphEdge(
                    source=row['parent_id'],
                    target=row['child_id'],
                    type="parent-child"
                ))
    else:
        cursor = db.conn.cursor()
        cursor.execute("SELECT parent_id, child_id FROM concept_relations")
        for row in cursor.fetchall():
            edges.append(GraphEdge(
                source=row['parent_id'],
                target=row['child_id'],
                type="parent-child"
            ))

    return GraphData(nodes=nodes, edges=edges)
```

- [ ] **Step 4: Commit**

```bash
git add backend/services/concept_service.py backend/services/research_service.py backend/routes/graph.py
git commit -m "feat: route concept queries through Neo4j with SQLite fallback"
```

---

### Task 4: CLI 增强与 .env 配置

**Files:**
- Modify: `mkg/cli.py`
- Modify: `.env.example`

- [ ] **Step 1: 修改 `.env.example`**

在 `.env.example` 中添加 `USE_NEO4J` 配置：

```
# ==================== Neo4j 数据库 ====================
USE_NEO4J=false
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

- [ ] **Step 2: 修改 `mkg/cli.py` 中的 neo4j 命令**

将现有的 `neo4j_test` 和 `neo4j_migrate` 命令替换为新的 `neo4j` 命令组：

```python
@app.command()
def neo4j_status():
    """查看 Neo4j 连接状态和图谱统计"""
    from mkg.neo4j_store import Neo4jStore

    console.print("\n[bold]Neo4j 状态[/bold]\n")

    store = Neo4jStore()
    if store.connected:
        console.print("[green]✓ Neo4j 已连接[/green]")
        stats = store.get_stats()
        console.print(f"  概念总数: {stats.get('total_concepts', 0)}")
        console.print(f"  关系总数: {stats.get('total_relations', 0)}")
        console.print(f"  根概念数: {stats.get('root_concepts', 0)}")
    else:
        console.print("[red]✗ Neo4j 未连接[/red]")
        console.print("\n请确保:")
        console.print("  1. Neo4j 服务已启动")
        console.print("  2. .env 中 USE_NEO4J=true 且配置正确")
    store.close()


@app.command()
def neo4j_sync():
    """从 SQLite 全量同步到 Neo4j"""
    from mkg.neo4j_store import Neo4jStore

    console.print("\n[bold]从 SQLite 同步到 Neo4j...[/bold]\n")

    store = Neo4jStore()
    if not store.connected:
        console.print("[red]Neo4j 未连接[/red]")
        return

    db = get_db()
    result = store.sync_all_from_sqlite(db)
    console.print(f"[green]✓ 同步完成[/green]")
    console.print(f"  概念同步: {result['concepts_synced']}")
    console.print(f"  关系统计: {result['relations_synced']}")
    store.close()


@app.command()
def neo4j_test():
    """测试 Neo4j 连接"""
    from mkg.neo4j_store import Neo4jStore

    console.print("\n[bold]测试 Neo4j 连接...[/bold]\n")

    store = Neo4jStore()
    if store.connected:
        console.print("[green]✓ Neo4j 连接成功[/green]")
        stats = store.get_stats()
        console.print(f"  概念总数: {stats.get('total_concepts', 0)}")
        console.print(f"  关系总数: {stats.get('total_relations', 0)}")
    else:
        console.print("[red]✗ Neo4j 连接失败[/red]")
        console.print("\n请确保:")
        console.print("  1. Neo4j 已启动")
        console.print("  2. .env 配置正确")
    store.close()
```

- [ ] **Step 3: Commit**

```bash
git add mkg/cli.py .env.example
git commit -m "feat: enhance CLI with neo4j status and sync commands"
```

---

### Task 5: 测试 Neo4jStore（Mock）

**Files:**
- Create: `tests/test_neo4j_store.py`

- [ ] **Step 1: 创建 `tests/test_neo4j_store.py`**

```python
"""
Neo4jStore 单元测试（mock driver）
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from mkg.neo4j_store import Neo4jStore


@pytest.fixture
def mock_neo4j():
    """创建 mock 的 Neo4jStore"""
    with patch('mkg.neo4j_store.GraphDatabase') as mock_driver:
        store = Neo4jStore.__new__(Neo4jStore)
        store.driver = MagicMock()
        store.connected = True
        yield store


def test_sync_concept_when_connected(mock_neo4j):
    """已连接时 sync_concept 应成功"""
    mock_neo4j.sync_concept({
        "id": "test-concept",
        "text": "Test Concept",
        "text_en": "Test",
        "text_zh": "测试",
        "category": "field",
        "paper_count": 5,
    })
    # 验证 driver.session 被调用
    mock_neo4j.driver.session.assert_called()


def test_sync_concept_when_not_connected():
    """未连接时 sync_concept 应返回 False"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.sync_concept({"id": "test", "text": "Test"})
    assert result is False


def test_sync_relation_when_not_connected():
    """未连接时 sync_relation 应返回 False"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.sync_relation("parent", "child")
    assert result is False


def test_get_tree_returns_empty_when_not_connected():
    """未连接时 get_tree 应返回空"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.get_tree()
    assert result == {}


def test_get_children_returns_empty_when_not_connected():
    """未连接时 get_children 应返回空列表"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.get_children("some-id")
    assert result == []


def test_get_stats_returns_empty_when_not_connected():
    """未连接时 get_stats 应返回空 dict"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.get_stats()
    assert result == {}


def test_get_graph_data_returns_empty_when_not_connected():
    """未连接时 get_graph_data 应返回空 nodes/edges"""
    store = Neo4jStore.__new__(Neo4jStore)
    store.connected = False
    store.driver = None

    result = store.get_graph_data()
    assert result == {'nodes': [], 'edges': []}
```

- [ ] **Step 2: 运行测试**

```bash
pytest tests/test_neo4j_store.py -v
```

Expected: 7 passed

- [ ] **Step 3: Commit**

```bash
git add tests/test_neo4j_store.py
git commit -m "test: add Neo4jStore unit tests with mocked driver"
```

---

## 依赖关系

```
Task 1 (Neo4jStore 核心) ──→ Task 2 (Repository 同步) ──→ Task 3 (API 集成)
                              └──→ Task 5 (测试)
                                        ↓
                            Task 4 (CLI) ─→ Task 6 (验证)
```

Task 3 依赖 Task 1 和 Task 2。
Task 4 和 Task 5 可并行（Task 5 只依赖 Task 1）。
Task 6 是最终验证。
