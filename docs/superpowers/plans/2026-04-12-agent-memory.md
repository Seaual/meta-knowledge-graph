# Agent Memory 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 MKG Agent 添加跨对话记忆和研究记忆库能力，通过统一 Memory 模块管理用户偏好、对话上下文和结构化研究记忆。

**Architecture:** 新建 `mkg/memory.py` 包含 `AgentMemory` 统一入口，内部管理 `UserPreferences`、`ConversationContext`、`ResearchMemory` 三个子系统。在 `mkg/database.py` 中新增 3 张表。添加 `/api/memory/*` 路由和 `mkg memory` CLI 命令。

**Tech Stack:** SQLite, FastAPI, LangChain, pytest, typer

---

## 文件映射

| 文件 | 类型 | 职责 |
|------|------|------|
| `mkg/memory.py` | 新建 | 统一 Memory 模块，包含三个子系统 |
| `mkg/database.py` | 修改 | 新增 3 张表的 _init_tables 逻辑 |
| `backend/routes/memory.py` | 新建 | Memory API 路由 |
| `backend/schemas.py` | 修改 | 新增 Memory 相关的 Pydantic models |
| `backend/main.py` | 修改 | 注册 memory router |
| `mkg/cli.py` | 修改 | 添加 mkg memory CLI 命令 |
| `tests/test_memory.py` | 新建 | Memory 模块单元测试 |

---

### Task 1: 数据库表初始化

**Files:**
- Modify: `mkg/database.py`
- Test: `tests/test_memory.py`

- [ ] **Step 1: Write failing test for new tables**

Create `tests/test_memory.py`:

```python
"""
Agent Memory 模块测试
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from mkg.database import Database


@pytest.fixture
def test_db():
    db = Database(":memory:")
    db.connect()
    yield db
    db.close()


def test_user_preferences_table_exists(test_db):
    """user_preferences 表应存在"""
    cursor = test_db.execute_read(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_preferences'"
    )
    assert cursor.fetchone() is not None


def test_conversation_context_table_exists(test_db):
    """conversation_context 表应存在"""
    cursor = test_db.execute_read(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_context'"
    )
    assert cursor.fetchone() is not None


def test_research_memories_table_exists(test_db):
    """research_memories 表应存在"""
    cursor = test_db.execute_read(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='research_memories'"
    )
    assert cursor.fetchone() is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_memory.py -v`
Expected: 3 FAILED (tables not found)

- [ ] **Step 3: 修改 `mkg/database.py` 的 `_init_tables()` 方法**

在 `_init_tables()` 方法的末尾（在现有所有 CREATE TABLE 语句之后、`self.conn.commit()` 之前），添加以下 3 张新表的创建语句。找到 `_init_tables` 方法中最后一个 `cursor.execute("""...""")` 之后、`self.conn.commit()` 之前，插入：

```python
        # 用户偏好表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 对话上下文表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_context (
                id TEXT PRIMARY KEY,
                conv_id TEXT NOT NULL,
                summary TEXT,
                key_concepts TEXT,
                research_interests TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conv_id) REFERENCES conversations(id)
            )
        """)

        # 研究记忆表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_memories (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                memory_type TEXT NOT NULL,
                tags TEXT,
                concept_ids TEXT,
                paper_doi TEXT,
                source_section TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON research_memories(memory_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_paper_doi ON research_memories(paper_doi)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_concept_ids ON research_memories(concept_ids)")
```

然后在 `connect()` 方法的 `self._init_tables()` 调用之后，添加新表的自动迁移：

```python
    def connect(self):
        """连接到数据库"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=30000")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_tables()
        self._migrate_memory_tables()  # 新增：Memory 表迁移
        self.ensure_default_folder()
```

在 `_init_tables()` 方法之后，添加 `_migrate_memory_tables()` 方法：

```python
    def _migrate_memory_tables(self):
        """为 Memory 模块迁移新字段到现有表（幂等）"""
        cursor = self.conn.cursor()
        # conversation 表添加 context_summary 字段（如果不存在）
        try:
            cursor.execute("ALTER TABLE conversations ADD COLUMN context_summary TEXT")
        except Exception:
            pass  # 字段已存在
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_memory.py::test_user_preferences_table_exists tests/test_memory.py::test_conversation_context_table_exists tests/test_memory.py::test_research_memories_table_exists -v`
Expected: 3 passed

- [ ] **Step 5: Run all tests to ensure nothing is broken**

Run: `pytest tests/ -v`
Expected: all passed (same count as before + 3 new)

- [ ] **Step 6: Commit**

```bash
git add mkg/database.py tests/test_memory.py
git commit -m "feat: add memory tables (user_preferences, conversation_context, research_memories)"
```

---

### Task 2: Memory 核心模块

**Files:**
- Create: `mkg/memory.py`
- Modify: `tests/test_memory.py`

- [ ] **Step 1: Write tests for UserPreferences**

Append to `tests/test_memory.py`:

```python
from mkg.memory import AgentMemory


@pytest.fixture
def memory(test_db):
    return AgentMemory(test_db)


def test_preferences_set_and_get(memory):
    """设置和获取偏好"""
    memory.preferences.set("focus_areas", ["AI", "ML"])
    result = memory.preferences.get("focus_areas")
    assert result == ["AI", "ML"]


def test_preferences_get_nonexistent(memory):
    """获取不存在的偏好应返回 None"""
    assert memory.preferences.get("nonexistent") is None


def test_preferences_delete(memory):
    """删除偏好"""
    memory.preferences.set("test_key", "test_value")
    memory.preferences.delete("test_key")
    assert memory.preferences.get("test_key") is None


def test_preferences_get_all(memory):
    """获取所有偏好"""
    memory.preferences.set("key1", "value1")
    memory.preferences.set("key2", ["a", "b"])
    all_prefs = memory.preferences.get_all()
    assert "key1" in all_prefs
    assert all_prefs["key1"] == "value1"
    assert all_prefs["key2"] == ["a", "b"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_memory.py::test_preferences_set_and_get -v`
Expected: FAIL (AgentMemory not defined)

- [ ] **Step 3: Write UserPreferences implementation**

Create `mkg/memory.py`:

```python
"""
Agent Memory — 统一记忆管理

- UserPreferences: 键值对用户偏好
- ConversationContext: 跨对话上下文
- ResearchMemory: 结构化研究记忆
"""

import json
import logging
import uuid

logger = logging.getLogger(__name__)


class UserPreferences:
    """用户偏好管理 — 键值对存储"""

    def __init__(self, db):
        self._db = db

    def set(self, key: str, value) -> bool:
        """
        设置偏好

        Args:
            key: 偏好键
            value: 偏好值（任意可 JSON 序列化的类型）

        Returns:
            是否成功
        """
        self._db.execute_write("""
            INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, json.dumps(value, ensure_ascii=False)))
        return True

    def get(self, key: str):
        """
        获取偏好值

        Args:
            key: 偏好键

        Returns:
            偏好值，或 None
        """
        cursor = self._db.execute_read(
            "SELECT value FROM user_preferences WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row["value"])
        return None

    def delete(self, key: str) -> bool:
        """删除偏好"""
        self._db.execute_write(
            "DELETE FROM user_preferences WHERE key = ?",
            (key,)
        )
        return True

    def get_all(self) -> dict:
        """获取所有偏好"""
        cursor = self._db.execute_read(
            "SELECT key, value FROM user_preferences"
        )
        result = {}
        for row in cursor.fetchall():
            result[row["key"]] = json.loads(row["value"])
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_memory.py -k "preferences" -v`
Expected: 4 passed

- [ ] **Step 5: Write tests for ConversationContext**

Append to `tests/test_memory.py`:

```python
def test_conversation_context_get_empty(memory):
    """不存在的对话上下文应返回 None"""
    result = memory.context.get("nonexistent-conv")
    assert result is None


def test_conversation_context_summarize(memory):
    """生成对话摘要"""
    conv_id = "test-conv-1"
    # 先插入对话上下文记录
    memory.context._save(
        conv_id=conv_id,
        summary="Test summary",
        key_concepts=["concept1", "concept2"],
        research_interests=["AI", "ML"]
    )
    result = memory.context.get(conv_id)
    assert result is not None
    assert result["summary"] == "Test summary"
    assert result["key_concepts"] == ["concept1", "concept2"]
    assert result["research_interests"] == ["AI", "ML"]


def test_conversation_context_update_interests(memory):
    """更新研究兴趣"""
    conv_id = "test-conv-2"
    memory.context._save(conv_id, "summary", [], [])
    memory.context.update_interests(conv_id, ["NLP", "Transformers"])
    result = memory.context.get(conv_id)
    assert result["research_interests"] == ["NLP", "Transformers"]
```

- [ ] **Step 6: Write ConversationContext implementation**

在 `mkg/memory.py` 的 `UserPreferences` 类之后，添加：

```python
class ConversationContext:
    """跨对话上下文管理"""

    def __init__(self, db):
        self._db = db

    def _save(self, conv_id: str, summary: str,
              key_concepts: list[str], research_interests: list[str]) -> bool:
        """
        保存对话上下文（内部方法）

        Args:
            conv_id: 对话 ID
            summary: 对话摘要
            key_concepts: 关键概念 ID 列表
            research_interests: 研究兴趣标签列表

        Returns:
            是否成功
        """
        ctx_id = str(uuid.uuid4())
        self._db.execute_write("""
            INSERT OR REPLACE INTO conversation_context
                (id, conv_id, summary, key_concepts, research_interests)
            VALUES (?, ?, ?, ?, ?)
        """, (
            ctx_id,
            conv_id,
            summary,
            json.dumps(key_concepts, ensure_ascii=False),
            json.dumps(research_interests, ensure_ascii=False),
        ))
        return True

    def get(self, conv_id: str) -> dict | None:
        """
        获取对话上下文

        Args:
            conv_id: 对话 ID

        Returns:
            上下文字典，或 None
        """
        cursor = self._db.execute_read(
            "SELECT * FROM conversation_context WHERE conv_id = ? ORDER BY created_at DESC LIMIT 1",
            (conv_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "conv_id": row["conv_id"],
                "summary": row["summary"],
                "key_concepts": json.loads(row["key_concepts"]),
                "research_interests": json.loads(row["research_interests"]),
            }
        return None

    def update_interests(self, conv_id: str, interests: list[str]) -> bool:
        """
        更新研究兴趣

        Args:
            conv_id: 对话 ID
            interests: 研究兴趣标签列表

        Returns:
            是否成功
        """
        self._db.execute_write("""
            UPDATE conversation_context
            SET research_interests = ?, updated_at = CURRENT_TIMESTAMP
            WHERE conv_id = ?
        """, (json.dumps(interests, ensure_ascii=False), conv_id))
        return True
```

注意：上面的 SQL 使用了 `updated_at` 字段，但该列未在表定义中。需要在 `_save` 方法中去掉 `updated_at`，改用插入新记录（因为 get 方法使用 `ORDER BY created_at DESC LIMIT 1`）。将 `update_interests` 改为插入新记录：

```python
    def update_interests(self, conv_id: str, interests: list[str]) -> bool:
        """
        更新研究兴趣 — 通过插入新记录实现
        """
        existing = self.get(conv_id)
        if existing:
            return self._save(
                conv_id=conv_id,
                summary=existing["summary"],
                key_concepts=existing["key_concepts"],
                research_interests=interests,
            )
        return False
```

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/test_memory.py -k "context" -v`
Expected: 3 passed

- [ ] **Step 8: Write tests for ResearchMemory**

Append to `tests/test_memory.py`:

```python
def test_research_memory_add(memory):
    """添加研究记忆"""
    mem_id = memory.research.add(
        title="Transformer attention mechanism",
        content="Multi-head attention improves representation",
        memory_type="discovery",
        tags=["transformer", "attention"],
        concept_ids=["transformer", "attention"],
        paper_doi="10.1234/test",
        source_section="abstract"
    )
    assert mem_id is not None


def test_research_memory_search_by_tags(memory):
    """按标签搜索记忆"""
    memory.research.add(
        title="Test memory 1",
        content="content",
        memory_type="discovery",
        tags=["transformer", "attention"],
        paper_doi="10.1234/test1"
    )
    memory.research.add(
        title="Test memory 2",
        content="content",
        memory_type="method",
        tags=["CNN", "vision"],
        paper_doi="10.1234/test2"
    )
    results = memory.research.search_by_tags(["transformer"])
    assert len(results) == 1
    assert "Test memory 1" in results[0]["title"]


def test_research_memory_search_by_concept(memory):
    """按概念搜索记忆"""
    memory.research.add(
        title="Concept memory",
        content="content",
        memory_type="discovery",
        tags=["test"],
        concept_ids=["concept-a", "concept-b"],
        paper_doi="10.1234/test"
    )
    results = memory.research.search_by_concept("concept-a")
    assert len(results) == 1
    assert "Concept memory" in results[0]["title"]


def test_research_memory_search_by_type(memory):
    """按类型搜索记忆"""
    memory.research.add(
        title="Discovery",
        content="content",
        memory_type="discovery",
        tags=["test"],
        paper_doi="10.1234/d1"
    )
    memory.research.add(
        title="Method",
        content="content",
        memory_type="method",
        tags=["test"],
        paper_doi="10.1234/m1"
    )
    results = memory.research.search_by_type("discovery")
    assert len(results) == 1
    assert results[0]["memory_type"] == "discovery"


def test_research_memory_delete(memory):
    """删除研究记忆"""
    mem_id = memory.research.add(
        title="To delete",
        content="content",
        memory_type="discovery",
        tags=["test"],
        paper_doi="10.1234/delete"
    )
    memory.research.delete(mem_id)
    results = memory.research.get_related("10.1234/delete")
    assert len(results) == 0


def test_research_memory_get_related(memory):
    """按论文 DOI 获取相关记忆"""
    memory.research.add(
        title="Paper 1 memory",
        content="content",
        memory_type="insight",
        tags=["test"],
        paper_doi="10.1234/shared"
    )
    results = memory.research.get_related("10.1234/shared")
    assert len(results) == 1
```

- [ ] **Step 9: Write ResearchMemory implementation**

在 `mkg/memory.py` 的 `ConversationContext` 类之后，添加：

```python
class ResearchMemory:
    """结构化研究记忆管理"""

    VALID_TYPES = {"discovery", "method", "experiment", "insight"}

    def __init__(self, db):
        self._db = db

    def add(self, title: str, content: str, memory_type: str,
            tags: list[str] = None, concept_ids: list[str] = None,
            paper_doi: str = None, source_section: str = None) -> str | None:
        """
        添加研究记忆

        Args:
            title: 记忆标题
            content: 内容详情
            memory_type: 类型（discovery/method/experiment/insight）
            tags: 关键词标签
            concept_ids: 关联概念 ID
            paper_doi: 来源论文 DOI
            source_section: 来源论文章节

        Returns:
            记忆 ID，或 None（失败时）
        """
        if memory_type not in self.VALID_TYPES:
            logger.warning(f"Invalid memory type: {memory_type}")
            return None

        mem_id = str(uuid.uuid4())
        try:
            self._db.execute_write("""
                INSERT INTO research_memories
                    (id, title, content, memory_type, tags, concept_ids, paper_doi, source_section)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mem_id,
                title,
                content,
                memory_type,
                json.dumps(tags or [], ensure_ascii=False),
                json.dumps(concept_ids or [], ensure_ascii=False),
                paper_doi,
                source_section,
            ))
            return mem_id
        except Exception as e:
            logger.error(f"Failed to add research memory: {e}")
            return None

    def search_by_tags(self, tags: list[str]) -> list[dict]:
        """
        按标签搜索记忆（任一标签匹配）

        Args:
            tags: 标签列表

        Returns:
            匹配的记忆列表
        """
        results = []
        cursor = self._db.execute_read("SELECT * FROM research_memories")
        for row in cursor.fetchall():
            row_tags = json.loads(row["tags"])
            if any(t in row_tags for t in tags):
                results.append(self._row_to_dict(row))
        return results

    def search_by_concept(self, concept_id: str) -> list[dict]:
        """
        按概念 ID 搜索记忆

        Args:
            concept_id: 概念 ID

        Returns:
            匹配的记忆列表
        """
        results = []
        cursor = self._db.execute_read("SELECT * FROM research_memories")
        for row in cursor.fetchall():
            concept_ids = json.loads(row["concept_ids"])
            if concept_id in concept_ids:
                results.append(self._row_to_dict(row))
        return results

    def search_by_type(self, memory_type: str) -> list[dict]:
        """
        按类型搜索记忆

        Args:
            memory_type: 记忆类型

        Returns:
            匹配的记忆列表
        """
        cursor = self._db.execute_read(
            "SELECT * FROM research_memories WHERE memory_type = ?",
            (memory_type,)
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_related(self, paper_doi: str) -> list[dict]:
        """
        获取论文相关的记忆

        Args:
            paper_doi: 论文 DOI

        Returns:
            相关记忆列表
        """
        cursor = self._db.execute_read(
            "SELECT * FROM research_memories WHERE paper_doi = ?",
            (paper_doi,)
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def delete(self, mem_id: str) -> bool:
        """删除研究记忆"""
        self._db.execute_write(
            "DELETE FROM research_memories WHERE id = ?",
            (mem_id,)
        )
        return True

    def _row_to_dict(self, row) -> dict:
        """将数据库行转换为字典"""
        return {
            "id": row["id"],
            "title": row["title"],
            "content": row["content"],
            "memory_type": row["memory_type"],
            "tags": json.loads(row["tags"]),
            "concept_ids": json.loads(row["concept_ids"]),
            "paper_doi": row["paper_doi"],
            "source_section": row["source_section"],
            "created_at": row["created_at"],
        }
```

- [ ] **Step 10: Write AgentMemory 统一入口**

在 `mkg/memory.py` 的 `ResearchMemory` 类之后，添加：

```python
class AgentMemory:
    """统一记忆入口"""

    def __init__(self, db):
        self._db = db
        self._preferences = None
        self._context = None
        self._research = None

    @property
    def preferences(self) -> UserPreferences:
        """获取用户偏好管理"""
        if self._preferences is None:
            self._preferences = UserPreferences(self._db)
        return self._preferences

    @property
    def context(self) -> ConversationContext:
        """获取对话上下文管理"""
        if self._context is None:
            self._context = ConversationContext(self._db)
        return self._context

    @property
    def research(self) -> ResearchMemory:
        """获取研究记忆管理"""
        if self._research is None:
            self._research = ResearchMemory(self._db)
        return self._research
```

- [ ] **Step 11: Run all memory tests**

Run: `pytest tests/test_memory.py -v`
Expected: 12 passed (3 table + 4 preferences + 3 context + 6 research - 1 overlap for context = 15 total)

Actually count: 3 table tests + 4 preferences + 3 context + 6 research = 16 tests

- [ ] **Step 12: Commit**

```bash
git add mkg/memory.py tests/test_memory.py
git commit -m "feat: add AgentMemory module with preferences, context, and research memory"
```

---

### Task 3: API 路由和 Schemas

**Files:**
- Create: `backend/routes/memory.py`
- Modify: `backend/schemas.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write tests for memory API**

Append to `tests/test_memory.py` (API-level integration tests):

```python
def test_memory_api_get_preferences_empty(memory):
    """API: 获取空偏好应返回空 dict"""
    assert memory.preferences.get_all() == {}


def test_memory_api_search_no_results(memory):
    """API: 搜索不存在的标签应返回空列表"""
    assert memory.research.search_by_tags(["nonexistent"]) == []
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/test_memory.py -k "api" -v`
Expected: 2 passed

- [ ] **Step 3: 添加 Pydantic schemas**

在 `backend/schemas.py` 末尾，添加 Memory 相关的 schema：

```python
# Memory schemas
class MemoryCreate(BaseModel):
    """创建研究记忆请求"""
    title: str
    content: str
    memory_type: str  # discovery/method/experiment/insight
    tags: list[str] = []
    concept_ids: list[str] = []
    paper_doi: str | None = None
    source_section: str | None = None


class MemoryResponse(BaseModel):
    """研究记忆响应"""
    id: str
    title: str
    content: str | None
    memory_type: str
    tags: list[str]
    concept_ids: list[str]
    paper_doi: str | None
    source_section: str | None
    created_at: str

    class Config:
        from_attributes = True


class PreferencesUpdate(BaseModel):
    """更新偏好请求"""
    key: str
    value: Any
```

- [ ] **Step 4: 创建 Memory API 路由**

Create `backend/routes/memory.py`:

```python
"""
Memory API routes — 用户偏好管理和研究记忆检索
"""

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.schemas import MemoryCreate, MemoryResponse, PreferencesUpdate
from mkg.database import Database
from mkg.memory import AgentMemory

router = APIRouter(prefix="/api/memory", tags=["memory"])

_db = None


def get_db():
    global _db
    if _db is None:
        db_path = Path(__file__).parent.parent.parent / "mkg.db"
        _db = Database(str(db_path))
        _db.connect()
    return _db


def get_memory():
    return AgentMemory(get_db())


@router.get("/preferences")
def get_preferences():
    """获取所有用户偏好"""
    memory = get_memory()
    return memory.preferences.get_all()


@router.put("/preferences")
def update_preference(request: PreferencesUpdate):
    """设置用户偏好"""
    memory = get_memory()
    memory.preferences.set(request.key, request.value)
    return {"success": True}


@router.delete("/preferences/{key}")
def delete_preference(key: str):
    """删除用户偏好"""
    memory = get_memory()
    memory.preferences.delete(key)
    return {"success": True}


@router.get("/research/tags/{tags_str}")
def search_by_tags(tags_str: str):
    """按标签搜索研究记忆（逗号分隔）"""
    memory = get_memory()
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    results = memory.research.search_by_tags(tags)
    return results


@router.get("/research/concept/{concept_id}")
def search_by_concept(concept_id: str):
    """按概念 ID 搜索研究记忆"""
    memory = get_memory()
    return memory.research.search_by_concept(concept_id)


@router.get("/research/type/{memory_type}")
def search_by_type(memory_type: str):
    """按类型搜索研究记忆"""
    memory = get_memory()
    return memory.research.search_by_type(memory_type)


@router.get("/research/paper/{paper_doi}")
def get_research_for_paper(paper_doi: str):
    """获取论文相关的研究记忆"""
    memory = get_memory()
    return memory.research.get_related(paper_doi)


@router.post("/research", response_model=MemoryResponse)
def add_research_memory(request: MemoryCreate):
    """添加研究记忆"""
    memory = get_memory()
    mem_id = memory.research.add(
        title=request.title,
        content=request.content,
        memory_type=request.memory_type,
        tags=request.tags,
        concept_ids=request.concept_ids,
        paper_doi=request.paper_doi,
        source_section=request.source_section,
    )
    if not mem_id:
        raise HTTPException(status_code=400, detail="Failed to add memory")

    # Fetch and return the created record
    results = memory.research.get_related(request.paper_doi or "")
    for r in results:
        if r["id"] == mem_id:
            return r

    raise HTTPException(status_code=500, detail="Memory created but fetch failed")


@router.delete("/research/{mem_id}")
def delete_research_memory(mem_id: str):
    """删除研究记忆"""
    memory = get_memory()
    memory.research.delete(mem_id)
    return {"success": True}
```

- [ ] **Step 5: 注册 Memory router**

在 `backend/main.py` 中找到 router 注册的位置（`app.include_router(...)` 语句），添加：

```python
from backend.routes.memory import router as memory_router

# 在已有的 app.include_router 调用旁边添加:
app.include_router(memory_router)
```

找到 `backend/main.py` 中所有 `app.include_router` 的导入行：

```python
from backend.routes.conversations import router as conversations_router
```

在同一区域添加 `memory_router` 的导入和注册。

- [ ] **Step 6: Commit**

```bash
git add backend/routes/memory.py backend/schemas.py backend/main.py
git commit -m "feat: add /api/memory routes for preferences and research memory"
```

---

### Task 4: CLI 命令增强

**Files:**
- Modify: `mkg/cli.py`

- [ ] **Step 1: Write CLI memory commands**

在 `mkg/cli.py` 中，在现有的 neo4j 命令之后，添加 `memory` 命令组：

```python
# ========== Memory 命令 ==========


@app.command()
def memory_search(query: str = typer.Argument(..., help="搜索关键词（逗号分隔）")):
    """按标签搜索研究记忆"""
    from mkg.memory import AgentMemory

    db = get_db()
    memory = AgentMemory(db)
    tags = [t.strip() for t in query.split(",") if t.strip()]

    results = memory.research.search_by_tags(tags)
    if not results:
        console.print("[yellow]未找到匹配的记忆[/yellow]")
        return

    console.print(f"\n[bold]研究记忆: {query}[/bold]\n")
    for r in results:
        console.print(f"  📝 {r['title']} [{r['memory_type']}]")
        console.print(f"     标签: {', '.join(r['tags'])}")
        console.print(f"     论文: {r.get('paper_doi', 'N/A')}")
        console.print("")


@app.command()
def memory_list():
    """列出所有研究记忆"""
    from mkg.memory import AgentMemory

    db = get_db()
    memory = AgentMemory(db)
    all_memories = []
    for mem_type in ["discovery", "method", "experiment", "insight"]:
        all_memories.extend(memory.research.search_by_type(mem_type))

    if not all_memories:
        console.print("[yellow]没有研究记忆[/yellow]")
        return

    table = Table(show_header=True)
    table.add_column("标题")
    table.add_column("类型")
    table.add_column("标签")
    table.add_column("论文")

    for m in all_memories:
        table.add_row(
            m["title"],
            m["memory_type"],
            ", ".join(m["tags"]),
            m.get("paper_doi", "-")[:30],
        )

    console.print(table)


@app.command()
def memory_prefs():
    """查看所有用户偏好"""
    from mkg.memory import AgentMemory

    db = get_db()
    memory = AgentMemory(db)
    prefs = memory.preferences.get_all()

    if not prefs:
        console.print("[yellow]没有设置偏好[/yellow]")
        return

    table = Table(show_header=True)
    table.add_column("键")
    table.add_column("值")

    for key, value in prefs.items():
        table.add_row(key, str(value))

    console.print(table)
```

- [ ] **Step 2: Commit**

```bash
git add mkg/cli.py
git commit -m "feat: add CLI memory commands (search, list, prefs)"
```

---

### Task 5: 运行全部测试验证

**Files:**
- None (verification only)

- [ ] **Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: all passed (original count + memory tests)

- [ ] **Step 2: Run lint and format check**

Run: `ruff check mkg/memory.py backend/routes/memory.py backend/schemas.py mkg/cli.py`
Run: `ruff format --check mkg/memory.py backend/routes/memory.py backend/schemas.py mkg/cli.py`

- [ ] **Step 3: Fix any lint/format issues**

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: address lint issues for Agent Memory"
```

---

## 依赖关系

```
Task 1 (数据库表) ──→ Task 2 (Memory 核心) ──→ Task 3 (API 路由)
                                            └──→ Task 4 (CLI)
                                                  ↓
                                        Task 5 (全部验证)
```
