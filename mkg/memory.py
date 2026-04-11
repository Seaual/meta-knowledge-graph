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
        self._db.execute_write(
            "INSERT OR REPLACE INTO user_preferences (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, json.dumps(value, ensure_ascii=False)),
        )
        return True

    def get(self, key: str):
        cursor = self._db.execute_read(
            "SELECT value FROM user_preferences WHERE key = ?",
            (key,),
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row["value"])
        return None

    def delete(self, key: str) -> bool:
        self._db.execute_write(
            "DELETE FROM user_preferences WHERE key = ?",
            (key,),
        )
        return True

    def get_all(self) -> dict:
        cursor = self._db.execute_read("SELECT key, value FROM user_preferences")
        result = {}
        for row in cursor.fetchall():
            result[row["key"]] = json.loads(row["value"])
        return result


class ConversationContext:
    """跨对话上下文管理"""

    def __init__(self, db):
        self._db = db

    def _save(
        self,
        conv_id: str,
        summary: str,
        key_concepts: list[str],
        research_interests: list[str],
    ) -> bool:
        ctx_id = str(uuid.uuid4())
        self._db.execute_write(
            "INSERT OR REPLACE INTO conversation_context (id, conv_id, summary, key_concepts, research_interests) VALUES (?, ?, ?, ?, ?)",
            (
                ctx_id,
                conv_id,
                summary,
                json.dumps(key_concepts, ensure_ascii=False),
                json.dumps(research_interests, ensure_ascii=False),
            ),
        )
        return True

    def get(self, conv_id: str) -> dict | None:
        cursor = self._db.execute_read(
            "SELECT * FROM conversation_context WHERE conv_id = ? ORDER BY created_at DESC LIMIT 1",
            (conv_id,),
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
        existing = self.get(conv_id)
        if existing:
            self._db.execute_write(
                "UPDATE conversation_context SET research_interests = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(interests, ensure_ascii=False), existing["id"]),
            )
            return True
        return False


class ResearchMemory:
    """结构化研究记忆管理"""

    VALID_TYPES = {"discovery", "method", "experiment", "insight"}

    def __init__(self, db):
        self._db = db

    def add(
        self,
        title: str,
        content: str,
        memory_type: str,
        tags: list[str] = None,
        concept_ids: list[str] = None,
        paper_doi: str = None,
        source_section: str = None,
    ) -> str | None:
        if memory_type not in self.VALID_TYPES:
            logger.warning(f"Invalid memory type: {memory_type}")
            return None

        mem_id = str(uuid.uuid4())
        try:
            self._db.execute_write(
                "INSERT INTO research_memories (id, title, content, memory_type, tags, concept_ids, paper_doi, source_section) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    mem_id,
                    title,
                    content,
                    memory_type,
                    json.dumps(tags or [], ensure_ascii=False),
                    json.dumps(concept_ids or [], ensure_ascii=False),
                    paper_doi,
                    source_section,
                ),
            )
            return mem_id
        except Exception as e:
            logger.error(f"Failed to add research memory: {e}")
            return None

    def search_by_tags(self, tags: list[str]) -> list[dict]:
        results = []
        cursor = self._db.execute_read("SELECT * FROM research_memories")
        for row in cursor.fetchall():
            row_tags = json.loads(row["tags"])
            if any(t in row_tags for t in tags):
                results.append(self._row_to_dict(row))
        return results

    def search_by_concept(self, concept_id: str) -> list[dict]:
        results = []
        cursor = self._db.execute_read("SELECT * FROM research_memories")
        for row in cursor.fetchall():
            if concept_id in json.loads(row["concept_ids"]):
                results.append(self._row_to_dict(row))
        return results

    def search_by_type(self, memory_type: str) -> list[dict]:
        cursor = self._db.execute_read(
            "SELECT * FROM research_memories WHERE memory_type = ?",
            (memory_type,),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_related(self, paper_doi: str) -> list[dict]:
        cursor = self._db.execute_read(
            "SELECT * FROM research_memories WHERE paper_doi = ?",
            (paper_doi,),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def delete(self, mem_id: str) -> bool:
        self._db.execute_write(
            "DELETE FROM research_memories WHERE id = ?",
            (mem_id,),
        )
        return True

    def _row_to_dict(self, row) -> dict:
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


class AgentMemory:
    """统一记忆入口"""

    def __init__(self, db):
        self._db = db
        self._preferences = None
        self._context = None
        self._research = None

    @property
    def preferences(self) -> UserPreferences:
        if self._preferences is None:
            self._preferences = UserPreferences(self._db)
        return self._preferences

    @property
    def context(self) -> ConversationContext:
        if self._context is None:
            self._context = ConversationContext(self._db)
        return self._context

    @property
    def research(self) -> ResearchMemory:
        if self._research is None:
            self._research = ResearchMemory(self._db)
        return self._research
