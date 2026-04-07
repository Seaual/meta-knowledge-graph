# Database.py 拆分重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 God Class `Database` (97 方法, 2146 行) 拆分为 7 个职责单一的 Repository 类。

**Architecture:** Repository 模式 - 每个领域一个 Repository 类，共享 Database 连接管理器，保留向后兼容层。

**Tech Stack:** Python 3.10+, SQLite, threading.Lock

---

## 文件结构

```
mkg/
├── database.py              # 修改：精简为连接管理器 + Repository 组合
└── repositories/            # 新建目录
    ├── __init__.py          # 导出所有 Repository
    ├── base.py              # 基础 Repository 类
    ├── paper_repo.py        # Paper 相关操作
    ├── concept_repo.py      # Concept 相关操作
    ├── folder_repo.py       # Folder 相关操作
    ├── config_repo.py       # LLM/S2 配置
    ├── conversation_repo.py # 会话管理
    ├── research_repo.py     # 研究会话
    └── citation_repo.py     # 引用关系

tests/
└── repositories/            # 新建测试目录
    ├── test_paper_repo.py
    ├── test_concept_repo.py
    └── ...
```

---

## Task 1: 创建 repositories 目录结构

**Files:**
- Create: `mkg/repositories/__init__.py`
- Create: `mkg/repositories/base.py`

- [ ] **Step 1: 创建 `mkg/repositories/__init__.py`**

```python
# mkg/repositories/__init__.py
"""
Repository 模块 - 数据访问层

每个 Repository 负责一个领域的数据库操作
"""

from .base import BaseRepository
from .paper_repo import PaperRepository
from .concept_repo import ConceptRepository
from .folder_repo import FolderRepository
from .config_repo import ConfigRepository
from .conversation_repo import ConversationRepository
from .research_repo import ResearchRepository
from .citation_repo import CitationRepository

__all__ = [
    "BaseRepository",
    "PaperRepository",
    "ConceptRepository",
    "FolderRepository",
    "ConfigRepository",
    "ConversationRepository",
    "ResearchRepository",
    "CitationRepository",
]
```

- [ ] **Step 2: 创建 `mkg/repositories/base.py`**

```python
# mkg/repositories/base.py
"""
基础 Repository 类 - 提供通用的数据库操作方法
"""

import json
import sqlite3
from typing import Optional, Dict, List, Any


class BaseRepository:
    """Repository 基类，提供通用数据库操作"""

    def __init__(self, db):
        """
        初始化 Repository

        Args:
            db: Database 实例，提供连接和线程安全的执行方法
        """
        self._db = db

    @property
    def conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return self._db.conn

    def execute_write(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行写操作（线程安全）"""
        return self._db.execute_write(query, params)

    def execute_read(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行读操作（线程安全）"""
        return self._db.execute_read(query, params)

    @staticmethod
    def _deserialize_json(value: Any, default: Any = None) -> Any:
        """反序列化 JSON 字段"""
        if value is None:
            return default
        if isinstance(value, (list, dict)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return default
        return default

    @staticmethod
    def _serialize_json(value: Any) -> str:
        """序列化为 JSON 字符串"""
        if value is None:
            return "[]"
        return json.dumps(value)
```

- [ ] **Step 3: 提交**

```bash
git add mkg/repositories/
git commit -m "feat(db): create repositories directory structure with BaseRepository"
```

---

## Task 2: 创建 PaperRepository

**Files:**
- Create: `mkg/repositories/paper_repo.py`

- [ ] **Step 1: 创建 `mkg/repositories/paper_repo.py`**

```python
# mkg/repositories/paper_repo.py
"""
Paper Repository - 论文相关数据库操作
"""

import json
from typing import Optional, Dict, List

from .base import BaseRepository


class PaperRepository(BaseRepository):
    """论文数据访问层"""

    # ========== CRUD ==========

    def add(self, paper_data: dict) -> str:
        """添加或更新论文"""
        cursor = self.conn.cursor()

        # 检查是否已存在
        cursor.execute("SELECT doi FROM papers WHERE doi = ?",
                      (paper_data.get('doi'),))
        existing = cursor.fetchone()

        if existing:
            # 更新
            cursor.execute("""
                UPDATE papers SET
                    title = ?, abstract = ?, authors = ?,
                    keywords = ?, contributions = ?,
                    pdf_path = ?, published_date = ?,
                    s2_paper_id = ?, venue = ?, year = ?,
                    citation_count = ?, reference_count = ?, influential_citation_count = ?,
                    open_access_pdf = ?, s2_doi = ?, s2_arxiv_id = ?, s2_external_ids = ?,
                    tldr = ?, s2_fields_of_study = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE doi = ?
            """, (
                paper_data.get('title'),
                paper_data.get('abstract'),
                self._serialize_json(paper_data.get('authors', [])),
                self._serialize_json(paper_data.get('keywords', [])),
                self._serialize_json(paper_data.get('contributions', [])),
                paper_data.get('pdf_path'),
                paper_data.get('published'),
                paper_data.get('s2_paper_id'),
                paper_data.get('venue'),
                paper_data.get('year'),
                paper_data.get('citation_count'),
                paper_data.get('reference_count'),
                paper_data.get('influential_citation_count'),
                paper_data.get('open_access_pdf'),
                paper_data.get('s2_doi'),
                paper_data.get('s2_arxiv_id'),
                paper_data.get('s2_external_ids'),
                paper_data.get('tldr'),
                paper_data.get('s2_fields_of_study'),
                paper_data.get('doi')
            ))
            doi = existing['doi']
        else:
            # 插入
            doi = paper_data.get('doi', paper_data.get('arxiv_id'))
            cursor.execute("""
                INSERT INTO papers (doi, arxiv_id, title, abstract, authors, keywords, contributions, 
                    pdf_path, published_date, status, s2_paper_id, venue, year, citation_count, 
                    reference_count, influential_citation_count, open_access_pdf, s2_doi, 
                    s2_arxiv_id, s2_external_ids, tldr, s2_fields_of_study)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doi,
                paper_data.get('arxiv_id'),
                paper_data.get('title'),
                paper_data.get('abstract'),
                self._serialize_json(paper_data.get('authors', [])),
                self._serialize_json(paper_data.get('keywords', [])),
                self._serialize_json(paper_data.get('contributions', [])),
                paper_data.get('pdf_path'),
                paper_data.get('published'),
                paper_data.get('s2_paper_id'),
                paper_data.get('venue'),
                paper_data.get('year'),
                paper_data.get('citation_count'),
                paper_data.get('reference_count'),
                paper_data.get('influential_citation_count'),
                paper_data.get('open_access_pdf'),
                paper_data.get('s2_doi'),
                paper_data.get('s2_arxiv_id'),
                paper_data.get('s2_external_ids'),
                paper_data.get('tldr'),
                paper_data.get('s2_fields_of_study'),
            ))

        self.conn.commit()
        return doi

    def get(self, identifier: str) -> Optional[dict]:
        """获取论文（支持 DOI、arXiv ID 或 S2 Paper ID）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM papers WHERE doi = ? OR arxiv_id = ? OR s2_paper_id = ?
        """, (identifier, identifier, identifier))
        row = cursor.fetchone()
        if row:
            return self._row_to_dict(row)
        return None

    def get_all(self, folder_id: str = None, status: str = None) -> list:
        """获取所有论文"""
        cursor = self.conn.cursor()
        if folder_id:
            cursor.execute("SELECT * FROM papers WHERE folder_id = ? ORDER BY created_at DESC", (folder_id,))
        elif status:
            cursor.execute("SELECT * FROM papers WHERE status = ? ORDER BY created_at DESC", (status,))
        else:
            cursor.execute("SELECT * FROM papers ORDER BY created_at DESC")
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_all_basic(self) -> List[dict]:
        """获取所有论文基本信息（用于下拉选择等）"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT doi, title, year, venue FROM papers ORDER BY title")
        return [dict(row) for row in cursor.fetchall()]

    def get_by_status(self, status: str) -> list:
        """按状态获取论文"""
        return self.get_all(status=status)

    def get_by_folder(self, folder_id: str) -> list:
        """按文件夹获取论文"""
        return self.get_all(folder_id=folder_id)

    def get_by_s2_id(self, s2_paper_id: str) -> Optional[dict]:
        """通过 S2 Paper ID 获取论文"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE s2_paper_id = ?", (s2_paper_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_dict(row)
        return None

    def get_with_s2_id(self) -> List[dict]:
        """获取所有有 S2 ID 的论文"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT doi, title, s2_paper_id FROM papers WHERE s2_paper_id IS NOT NULL")
        return [dict(row) for row in cursor.fetchall()]

    def update_status(self, doi: str, status: str, error_message: str = None):
        """更新论文处理状态"""
        self.execute_write("""
            UPDATE papers SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE doi = ?
        """, (status, error_message, doi))

    def update_metadata(self, doi: str, metadata: dict):
        """更新论文元数据"""
        fields = []
        values = []
        for key in ['title', 'abstract', 'venue', 'year', 'citation_count', 'tldr']:
            if key in metadata:
                fields.append(f"{key} = ?")
                values.append(metadata[key])
        if not fields:
            return
        values.append(doi)
        self.execute_write(f"""
            UPDATE papers SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE doi = ?
        """, tuple(values))

    def update_s2_metadata(self, doi: str, metadata: dict):
        """更新 S2 相关元数据"""
        self.execute_write("""
            UPDATE papers SET
                s2_paper_id = ?, s2_doi = ?, venue = ?, year = ?,
                citation_count = ?, reference_count = ?, influential_citation_count = ?,
                open_access_pdf = ?, tldr = ?, s2_fields_of_study = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE doi = ?
        """, (
            metadata.get('s2_paper_id'),
            metadata.get('s2_doi'),
            metadata.get('venue'),
            metadata.get('year'),
            metadata.get('citation_count'),
            metadata.get('reference_count'),
            metadata.get('influential_citation_count'),
            metadata.get('open_access_pdf'),
            metadata.get('tldr'),
            metadata.get('s2_fields_of_study'),
            doi
        ))

    def add_pdf_path(self, doi: str, pdf_path: str):
        """更新 PDF 路径"""
        self.execute_write("""
            UPDATE papers SET pdf_path = ?, status = 'downloaded', updated_at = CURRENT_TIMESTAMP
            WHERE doi = ?
        """, (pdf_path, doi))

    def move_to_folder(self, doi: str, folder_id: str):
        """移动论文到文件夹"""
        self.execute_write("UPDATE papers SET folder_id = ? WHERE doi = ?", (folder_id, doi))

    def delete(self, doi: str):
        """删除论文（仅删除论文记录，不处理关联）"""
        self.execute_write("DELETE FROM papers WHERE doi = ?", (doi,))

    # ========== 概念关联 ==========

    def get_concepts(self, paper_doi: str) -> list:
        """获取论文关联的概念"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.* FROM concepts c
            JOIN paper_concepts pc ON c.id = pc.concept_id
            WHERE pc.paper_doi = ?
            ORDER BY pc.relevance DESC
        """, (paper_doi,))
        return [dict(row) for row in cursor.fetchall()]

    def get_contribution(self, doi: str) -> dict:
        """获取论文贡献统计"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as node_count FROM paper_concepts WHERE paper_doi = ?
        """, (doi,))
        row = cursor.fetchone()
        return {"node_count": row['node_count'] if row else 0}

    # ========== 处理日志 ==========

    def log_processing(self, paper_doi: str, action: str, status: str, message: str = None):
        """记录处理日志"""
        self.execute_write("""
            INSERT OR REPLACE INTO processing_log (paper_doi, action, status, message, timestamp)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (paper_doi, action, status, message))

    # ========== 私有方法 ==========

    def _row_to_dict(self, row) -> dict:
        """将数据库行转换为字典，处理 JSON 字段"""
        paper = dict(row)
        paper['authors'] = self._deserialize_json(paper.get('authors'), [])
        paper['keywords'] = self._deserialize_json(paper.get('keywords'), [])
        paper['contributions'] = self._deserialize_json(paper.get('contributions'), [])
        paper['s2_fields_of_study'] = self._deserialize_json(paper.get('s2_fields_of_study'), [])
        return paper
```

- [ ] **Step 2: 提交**

```bash
git add mkg/repositories/paper_repo.py mkg/repositories/__init__.py
git commit -m "feat(db): add PaperRepository with CRUD and S2 integration"
```

---

## Task 3: 创建 ConceptRepository

**Files:**
- Create: `mkg/repositories/concept_repo.py`

- [ ] **Step 1: 创建 `mkg/repositories/concept_repo.py`**

```python
# mkg/repositories/concept_repo.py
"""
Concept Repository - 概念相关数据库操作
"""

import re
from typing import Optional, Dict, List

from .base import BaseRepository


class ConceptRepository(BaseRepository):
    """概念数据访问层"""

    # ========== CRUD ==========

    def add(self, concept_data: dict) -> str:
        """添加概念，返回概念 ID"""
        cursor = self.conn.cursor()
        concept_id = concept_data.get('id') or self._to_slug(concept_data.get('text', ''))

        cursor.execute("""
            INSERT OR IGNORE INTO concepts (id, text, text_en, text_zh, category, paper_count)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (
            concept_id,
            concept_data.get('text'),
            concept_data.get('text_en'),
            concept_data.get('text_zh'),
            concept_data.get('category')
        ))
        self.conn.commit()
        return concept_id

    def get(self, concept_id: str) -> Optional[dict]:
        """获取概念"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM concepts WHERE id = ?", (concept_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_by_text(self, text: str) -> Optional[dict]:
        """通过文本获取概念"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM concepts WHERE text = ?", (text,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all(self) -> list:
        """获取所有概念"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM concepts ORDER BY paper_count DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_root(self) -> list:
        """获取根概念（没有父节点的概念）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.* FROM concepts c
            WHERE NOT EXISTS (
                SELECT 1 FROM concept_relations cr WHERE cr.child_id = c.id
            )
            ORDER BY c.paper_count DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_count(self, folder_id: str = None) -> int:
        """获取概念数量"""
        cursor = self.conn.cursor()
        if folder_id:
            cursor.execute("""
                SELECT COUNT(DISTINCT c.id) as count FROM concepts c
                JOIN paper_concepts pc ON c.id = pc.concept_id
                JOIN papers p ON pc.paper_doi = p.doi
                WHERE p.folder_id = ?
            """, (folder_id,))
        else:
            cursor.execute("SELECT COUNT(*) as count FROM concepts")
        return cursor.fetchone()['count']

    def delete(self, concept_id: str):
        """删除概念"""
        self.execute_write("DELETE FROM concepts WHERE id = ?", (concept_id,))

    # ========== 层级关系 ==========

    def get_children(self, concept_id: str) -> list:
        """获取子概念"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.* FROM concepts c
            JOIN concept_relations cr ON c.id = cr.child_id
            WHERE cr.parent_id = ?
            ORDER BY c.paper_count DESC
        """, (concept_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_parents(self, concept_id: str) -> list:
        """获取父概念"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.* FROM concepts c
            JOIN concept_relations cr ON c.id = cr.parent_id
            WHERE cr.child_id = ?
        """, (concept_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_tree(self, root_id: str = None) -> dict:
        """获取概念树"""
        if root_id:
            root = self.get(root_id)
            if not root:
                return {}
            root['children'] = self._build_tree(root_id)
            return root
        else:
            roots = self.get_root()
            return {'roots': [dict(r, children=self._build_tree(r['id'])) for r in roots]}

    def add_relation(self, parent_id: str, child_id: str, relation_type: str = "parent-child"):
        """添加概念关系"""
        self.execute_write("""
            INSERT OR IGNORE INTO concept_relations (parent_id, child_id, relation_type)
            VALUES (?, ?, ?)
        """, (parent_id, child_id, relation_type))

    def update_relations(self, concept_id: str, relations: dict):
        """更新概念关系"""
        # 删除旧关系
        self.execute_write("DELETE FROM concept_relations WHERE child_id = ?", (concept_id,))
        # 添加新关系
        for parent_id in relations.get('parents', []):
            self.add_relation(parent_id, concept_id)

    # ========== 分类与文件夹 ==========

    def get_by_category(self, category: str) -> list:
        """按分类获取概念"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM concepts WHERE category = ? ORDER BY paper_count DESC", (category,))
        return [dict(row) for row in cursor.fetchall()]

    def get_by_category_and_folder(self, category: str, folder_id: str) -> list:
        """按分类和文件夹获取概念"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT c.* FROM concepts c
            JOIN paper_concepts pc ON c.id = pc.concept_id
            JOIN papers p ON pc.paper_doi = p.doi
            WHERE c.category = ? AND p.folder_id = ?
            ORDER BY c.paper_count DESC
        """, (category, folder_id))
        return [dict(row) for row in cursor.fetchall()]

    def get_by_folder(self, folder_id: str) -> list:
        """按文件夹获取概念"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT c.* FROM concepts c
            JOIN paper_concepts pc ON c.id = pc.concept_id
            JOIN papers p ON pc.paper_doi = p.doi
            WHERE p.folder_id = ?
            ORDER BY c.paper_count DESC
        """, (folder_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_relations_by_folder(self, folder_id: str) -> list:
        """获取文件夹内的概念关系"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT cr.* FROM concept_relations cr
            JOIN paper_concepts pc1 ON cr.parent_id = pc1.concept_id
            JOIN papers p1 ON pc1.paper_doi = p1.doi
            JOIN paper_concepts pc2 ON cr.child_id = pc2.concept_id
            JOIN papers p2 ON pc2.paper_doi = p2.doi
            WHERE p1.folder_id = ? AND p2.folder_id = ?
        """, (folder_id, folder_id))
        return [dict(row) for row in cursor.fetchall()]

    # ========== 论文关联 ==========

    def get_papers(self, concept_id: str) -> list:
        """获取概念关联的论文"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.* FROM papers p
            JOIN paper_concepts pc ON p.doi = pc.paper_doi
            WHERE pc.concept_id = ?
            ORDER BY pc.relevance DESC
        """, (concept_id,))
        return [dict(row) for row in cursor.fetchall()]

    def add_paper_concept(self, paper_doi: str, concept_id: str, relevance: float = 1.0):
        """添加论文-概念关联"""
        self.execute_write("""
            INSERT OR REPLACE INTO paper_concepts (paper_doi, concept_id, relevance)
            VALUES (?, ?, ?)
        """, (paper_doi, concept_id, relevance))
        # 更新概念论文计数
        self._update_paper_count(concept_id)

    # ========== 概念提取 ==========

    def save_extraction(self, paper_doi: str, hierarchy: dict, raw_response: str):
        """保存概念提取结果"""
        self.execute_write("""
            INSERT OR REPLACE INTO concept_extractions (paper_doi, hierarchy, raw_response, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (paper_doi, hierarchy, raw_response))

    def get_extraction(self, paper_doi: str) -> Optional[dict]:
        """获取概念提取结果"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM concept_extractions WHERE paper_doi = ?", (paper_doi,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # ========== 深度缓存 ==========

    def recalculate_depth_cache(self, concept_id: str = None):
        """重新计算深度缓存"""
        if concept_id:
            self._calculate_depth(concept_id)
        else:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM concepts")
            for row in cursor.fetchall():
                self._calculate_depth(row['id'])

    # ========== 内部方法 ==========

    def _build_tree(self, parent_id: str) -> list:
        """递归构建概念树"""
        children = self.get_children(parent_id)
        for child in children:
            child['children'] = self._build_tree(child['id'])
        return children

    def _update_paper_count(self, concept_id: str):
        """更新概念论文计数"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE concepts SET paper_count = (
                SELECT COUNT(*) FROM paper_concepts WHERE concept_id = ?
            ) WHERE id = ?
        """, (concept_id, concept_id))
        self.conn.commit()

    def _calculate_depth(self, concept_id: str, visited: set = None) -> int:
        """计算概念深度"""
        if visited is None:
            visited = set()
        if concept_id in visited:
            return 0
        visited.add(concept_id)

        parents = self.get_parents(concept_id)
        if not parents:
            depth = 0
        else:
            depth = 1 + max(self._calculate_depth(p['id'], visited) for p in parents)

        # 更新深度缓存
        self.execute_write("UPDATE concepts SET depth_cache = ? WHERE id = ?", (depth, concept_id))
        return depth

    def _delete_orphaned(self, concept_id: str):
        """删除孤立概念（没有论文关联的概念）"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM paper_concepts WHERE concept_id = ?", (concept_id,))
        if cursor.fetchone()['count'] == 0:
            self.delete(concept_id)

    @staticmethod
    def _to_slug(text: str) -> str:
        """将文本转换为 slug"""
        if not text:
            return ""
        # 转小写
        slug = text.lower().strip()
        # 替换空格和特殊字符
        slug = re.sub(r'[\s\-]+', '-', slug)
        slug = re.sub(r'[^\w\-]', '', slug)
        # 移除首尾连字符
        slug = slug.strip('-')
        return slug or "concept"
```

- [ ] **Step 2: 提交**

```bash
git add mkg/repositories/concept_repo.py mkg/repositories/__init__.py
git commit -m "feat(db): add ConceptRepository with hierarchy support"
```

---

## Task 4: 创建剩余 Repository 类

**Files:**
- Create: `mkg/repositories/folder_repo.py`
- Create: `mkg/repositories/config_repo.py`
- Create: `mkg/repositories/conversation_repo.py`
- Create: `mkg/repositories/research_repo.py`
- Create: `mkg/repositories/citation_repo.py`

- [ ] **Step 1: 创建 `mkg/repositories/folder_repo.py`**

```python
# mkg/repositories/folder_repo.py
"""
Folder Repository - 文件夹相关数据库操作
"""

from typing import Optional, List

from .base import BaseRepository
from .concept_repo import ConceptRepository


class FolderRepository(BaseRepository):
    """文件夹数据访问层"""

    def create(self, name: str, description: str = None) -> str:
        """创建文件夹"""
        from .concept_repo import ConceptRepository
        folder_id = ConceptRepository._to_slug(name)
        self.execute_write("""
            INSERT OR IGNORE INTO folders (id, name, description)
            VALUES (?, ?, ?)
        """, (folder_id, name, description))
        return folder_id

    def get(self, folder_id: str) -> Optional[dict]:
        """获取文件夹"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM folders WHERE id = ?", (folder_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all(self) -> List[dict]:
        """获取所有文件夹"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM folders ORDER BY created_at")
        return [dict(row) for row in cursor.fetchall()]

    def update(self, folder_id: str, name: str = None, description: str = None):
        """更新文件夹"""
        if name:
            self.execute_write("UPDATE folders SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                              (name, folder_id))
        if description is not None:
            self.execute_write("UPDATE folders SET description = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                              (description, folder_id))

    def delete(self, folder_id: str) -> bool:
        """删除文件夹（不能删除默认文件夹）"""
        if folder_id == 'default':
            return False
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM folders WHERE id = ?", (folder_id,))
        if not cursor.fetchone():
            return False
        self.execute_write("DELETE FROM folders WHERE id = ?", (folder_id,))
        return True

    def ensure_default(self) -> str:
        """确保默认文件夹存在"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM folders WHERE id = 'default'")
        if not cursor.fetchone():
            self.execute_write("""
                INSERT INTO folders (id, name, description)
                VALUES ('default', '默认', '默认文件夹')
            """)
        return 'default'
```

- [ ] **Step 2: 创建 `mkg/repositories/config_repo.py`**

```python
# mkg/repositories/config_repo.py
"""
Config Repository - 配置相关数据库操作（LLM、S2）
"""

from typing import Optional, Dict, List

from .base import BaseRepository


class ConfigRepository(BaseRepository):
    """配置数据访问层"""

    # ========== LLM 配置 ==========

    def get_llm_config(self) -> Optional[Dict]:
        """获取 LLM 配置"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM llm_config ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return None

        config = dict(row)
        config_id = config['id']

        cursor.execute("SELECT * FROM llm_provider_config WHERE config_id = ?", (config_id,))
        providers = [dict(r) for r in cursor.fetchall()]
        config['providers'] = providers

        return config

    def save_llm_config(self, mode: str, providers: List[Dict]) -> Dict:
        """保存 LLM 配置"""
        cursor = self.conn.cursor()

        # 清除旧配置
        cursor.execute("DELETE FROM llm_provider_config")
        cursor.execute("DELETE FROM llm_config")

        # 插入新配置
        cursor.execute("INSERT INTO llm_config (mode) VALUES (?)", (mode,))
        config_id = cursor.lastrowid

        for p in providers:
            cursor.execute("""
                INSERT INTO llm_provider_config
                (config_id, function_group, provider, api_key, base_url, model, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                config_id,
                p.get('function_group'),
                p['provider'],
                p.get('api_key'),
                p.get('base_url'),
                p.get('model'),
                p.get('is_active', True)
            ))

        self.conn.commit()
        return self.get_llm_config()

    def get_llm_provider_for_function(self, function_group: str) -> Optional[Dict]:
        """获取指定功能的 LLM 提供商配置"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.* FROM llm_provider_config p
            JOIN llm_config c ON p.config_id = c.id
            WHERE c.mode = 'per_function' AND p.function_group = ? AND p.is_active = 1
        """, (function_group,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_active_llm_provider(self) -> Optional[Dict]:
        """获取活跃的 LLM 提供商（单模式）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.* FROM llm_provider_config p
            JOIN llm_config c ON p.config_id = c.id
            WHERE c.mode = 'single' AND p.is_active = 1
            LIMIT 1
        """)
        row = cursor.fetchone()
        return dict(row) if row else None

    # ========== S2 配置 ==========

    def get_s2_config(self) -> Optional[Dict]:
        """获取 Semantic Scholar 配置"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM s2_config ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def save_s2_config(self, api_key: str, enabled: bool = True) -> Dict:
        """保存 S2 配置"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM s2_config")
        cursor.execute("""
            INSERT INTO s2_config (api_key, enabled)
            VALUES (?, ?)
        """, (api_key, enabled))
        self.conn.commit()
        return self.get_s2_config()
```

- [ ] **Step 3: 创建 `mkg/repositories/conversation_repo.py`**

```python
# mkg/repositories/conversation_repo.py
"""
Conversation Repository - 会话相关数据库操作
"""

import uuid
import json
from typing import Optional, List

from .base import BaseRepository


class ConversationRepository(BaseRepository):
    """会话数据访问层"""

    def create(self, device_id: str) -> str:
        """创建新会话"""
        conv_id = str(uuid.uuid4())
        self.execute_write("""
            INSERT INTO conversations (id, device_id)
            VALUES (?, ?)
        """, (conv_id, device_id))
        return conv_id

    def get(self, conv_id: str) -> Optional[dict]:
        """获取会话"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all(self, device_id: str, limit: int = 50) -> List[dict]:
        """获取设备的所有会话"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM conversations 
            WHERE device_id = ? 
            ORDER BY updated_at DESC 
            LIMIT ?
        """, (device_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def update_title(self, conv_id: str, title: str):
        """更新会话标题"""
        self.execute_write("""
            UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (title, conv_id))

    def update_timestamp(self, conv_id: str):
        """更新会话时间戳"""
        self.execute_write("""
            UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
        """, (conv_id,))

    def delete(self, conv_id: str):
        """删除会话及其消息"""
        self.execute_write("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        self.execute_write("DELETE FROM conversations WHERE id = ?", (conv_id,))

    # ========== 消息 ==========

    def get_messages(self, conv_id: str) -> List[dict]:
        """获取会话消息"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM messages 
            WHERE conversation_id = ? 
            ORDER BY created_at
        """, (conv_id,))
        messages = []
        for row in cursor.fetchall():
            msg = dict(row)
            if msg.get('attachments') and isinstance(msg['attachments'], str):
                msg['attachments'] = json.loads(msg['attachments'])
            messages.append(msg)
        return messages

    def add_message(self, conv_id: str, role: str, content: str, 
                   agent: str = None, attachments: List = None):
        """添加消息"""
        msg_id = str(uuid.uuid4())
        attachments_json = json.dumps(attachments) if attachments else None
        self.execute_write("""
            INSERT INTO messages (id, conversation_id, role, content, agent, attachments)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (msg_id, conv_id, role, content, agent, attachments_json))
        # 更新会话时间戳
        self.update_timestamp(conv_id)
```

- [ ] **Step 4: 创建 `mkg/repositories/research_repo.py`**

```python
# mkg/repositories/research_repo.py
"""
Research Repository - 研究会话相关数据库操作
"""

from typing import Optional, Dict, List

from .base import BaseRepository


class ResearchRepository(BaseRepository):
    """研究会话数据访问层"""

    def create_session(self, session_id: str, target_type: str, target_id: str, query: str):
        """创建研究会话"""
        self.execute_write("""
            INSERT INTO research_sessions (id, target_type, target_id, query)
            VALUES (?, ?, ?, ?)
        """, (session_id, target_type, target_id, query))

    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取研究会话"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM research_sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_progress(self, session_id: str, progress: int, dimensions: List[str]):
        """更新研究进度"""
        import json
        self.execute_write("""
            UPDATE research_sessions 
            SET progress = ?, dimensions = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (progress, json.dumps(dimensions), session_id))

    def save_finding(self, session_id: str, dimension: str, finding: str, confidence: float = None):
        """保存研究发现"""
        self.execute_write("""
            INSERT INTO research_findings (session_id, dimension, finding, confidence)
            VALUES (?, ?, ?, ?)
        """, (session_id, dimension, finding, confidence))

    def get_findings(self, session_id: str) -> List[Dict]:
        """获取研究发现"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM research_findings WHERE session_id = ?", (session_id,))
        return [dict(row) for row in cursor.fetchall()]

    def save_report(self, session_id: str, report: str):
        """保存研究报告"""
        self.execute_write("""
            UPDATE research_sessions SET report = ?, status = 'completed', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (report, session_id))

    # ========== S2 推荐 ==========

    def add_s2_recommendation(self, source_type: str, source_id: str, paper_data: Dict):
        """添加 S2 推荐"""
        import json
        self.execute_write("""
            INSERT INTO s2_recommendations (source_type, source_id, paper_id, paper_data)
            VALUES (?, ?, ?, ?)
        """, (source_type, source_id, paper_data.get('paperId'), json.dumps(paper_data)))

    def get_s2_recommendations(self, source_type: str, source_id: str) -> List[Dict]:
        """获取 S2 推荐"""
        import json
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM s2_recommendations 
            WHERE source_type = ? AND source_id = ?
            ORDER BY created_at DESC
        """, (source_type, source_id))
        results = []
        for row in cursor.fetchall():
            r = dict(row)
            if r.get('paper_data'):
                r['paper_data'] = json.loads(r['paper_data'])
            results.append(r)
        return results

    def clear_s2_recommendations(self, source_type: str = None, source_id: str = None):
        """清除 S2 推荐"""
        if source_type and source_id:
            self.execute_write(
                "DELETE FROM s2_recommendations WHERE source_type = ? AND source_id = ?",
                (source_type, source_id)
            )
        elif source_type:
            self.execute_write("DELETE FROM s2_recommendations WHERE source_type = ?", (source_type,))
        else:
            self.execute_write("DELETE FROM s2_recommendations")
```

- [ ] **Step 5: 创建 `mkg/repositories/citation_repo.py`**

```python
# mkg/repositories/citation_repo.py
"""
Citation Repository - 引用关系相关数据库操作
"""

from typing import Optional, Dict, List

from .base import BaseRepository


class CitationRepository(BaseRepository):
    """引用关系数据访问层"""

    def add(self, paper_doi: str, citation_data: Dict):
        """添加引用"""
        self.execute_write("""
            INSERT OR REPLACE INTO citations 
            (paper_doi, s2_paper_id, title, year, venue, authors, is_internal)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            paper_doi,
            citation_data.get('paper_id'),
            citation_data.get('title'),
            citation_data.get('year'),
            citation_data.get('venue'),
            citation_data.get('authors'),
            citation_data.get('is_internal', False)
        ))

    def get_all(self) -> List[Dict]:
        """获取所有引用"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM citations")
        return [dict(row) for row in cursor.fetchall()]

    def get_by_s2_id(self, s2_id: str) -> Optional[Dict]:
        """通过 S2 ID 获取引用"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM citations WHERE s2_paper_id = ?", (s2_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_paper_citations(self, paper_doi: str) -> List[Dict]:
        """获取论文引用的其他论文"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM citations WHERE paper_doi = ? AND is_internal = 0
        """, (paper_doi,))
        return [dict(row) for row in cursor.fetchall()]

    def get_paper_cited_by(self, paper_doi: str) -> List[Dict]:
        """获取引用该论文的论文"""
        cursor = self.conn.cursor()
        # 需要查询所有引用中，s2_paper_id 匹配该论文的
        cursor.execute("""
            SELECT c.*, p.doi as citing_doi, p.title as citing_title
            FROM citations c
            JOIN papers p ON c.paper_doi = p.doi
            WHERE c.s2_paper_id = (SELECT s2_paper_id FROM papers WHERE doi = ?)
        """, (paper_doi,))
        return [dict(row) for row in cursor.fetchall()]

    def get_internal_edges(self) -> List[Dict]:
        """获取内部引用关系边"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                p1.doi as source, p1.title as source_title,
                p2.doi as target, p2.title as target_title
            FROM citations c
            JOIN papers p1 ON c.paper_doi = p1.doi
            JOIN papers p2 ON c.s2_paper_id = p2.s2_paper_id
            WHERE c.is_internal = 1
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_all_edges(self) -> List[Dict]:
        """获取所有引用关系边"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                p.doi as source, p.title as source_title,
                c.s2_paper_id as target, c.title as target_title
            FROM citations c
            JOIN papers p ON c.paper_doi = p.doi
        """)
        return [dict(row) for row in cursor.fetchall()]

    def clear_paper_citations(self, paper_doi: str = None):
        """清除论文引用"""
        if paper_doi:
            self.execute_write("DELETE FROM citations WHERE paper_doi = ?", (paper_doi,))
        else:
            self.execute_write("DELETE FROM citations")
```

- [ ] **Step 6: 更新 `mkg/repositories/__init__.py` 确保导出正确**

```python
# mkg/repositories/__init__.py
"""
Repository 模块 - 数据访问层

每个 Repository 负责一个领域的数据库操作
"""

from .base import BaseRepository
from .paper_repo import PaperRepository
from .concept_repo import ConceptRepository
from .folder_repo import FolderRepository
from .config_repo import ConfigRepository
from .conversation_repo import ConversationRepository
from .research_repo import ResearchRepository
from .citation_repo import CitationRepository

__all__ = [
    "BaseRepository",
    "PaperRepository",
    "ConceptRepository",
    "FolderRepository",
    "ConfigRepository",
    "ConversationRepository",
    "ResearchRepository",
    "CitationRepository",
]
```

- [ ] **Step 7: 提交**

```bash
git add mkg/repositories/
git commit -m "feat(db): add FolderRepository, ConfigRepository, ConversationRepository, ResearchRepository, CitationRepository"
```

---

## Task 5: 修改 Database 类集成 Repository

**Files:**
- Modify: `mkg/database.py`

- [ ] **Step 1: 在 Database.__init__ 中初始化 Repository**

在 `mkg/database.py` 的 `__init__` 方法中添加 Repository 初始化：

```python
def __init__(self, db_path: str = "mkg.db"):
    self.db_path = Path(db_path)
    self.conn: Optional[sqlite3.Connection] = None
    self._lock = threading.Lock()
    
    # Repository 实例（延迟初始化）
    self._papers = None
    self._concepts = None
    self._folders = None
    self._config = None
    self._conversations = None
    self._research = None
    self._citations = None
```

- [ ] **Step 2: 添加 Repository 属性访问器**

在 `Database` 类中添加属性：

```python
@property
def papers(self) -> 'PaperRepository':
    """获取 Paper Repository"""
    if self._papers is None:
        from .repositories import PaperRepository
        self._papers = PaperRepository(self)
    return self._papers

@property
def concepts(self) -> 'ConceptRepository':
    """获取 Concept Repository"""
    if self._concepts is None:
        from .repositories import ConceptRepository
        self._concepts = ConceptRepository(self)
    return self._concepts

@property
def folders(self) -> 'FolderRepository':
    """获取 Folder Repository"""
    if self._folders is None:
        from .repositories import FolderRepository
        self._folders = FolderRepository(self)
    return self._folders

@property
def config(self) -> 'ConfigRepository':
    """获取 Config Repository"""
    if self._config is None:
        from .repositories import ConfigRepository
        self._config = ConfigRepository(self)
    return self._config

@property
def conversations(self) -> 'ConversationRepository':
    """获取 Conversation Repository"""
    if self._conversations is None:
        from .repositories import ConversationRepository
        self._conversations = ConversationRepository(self)
    return self._conversations

@property
def research(self) -> 'ResearchRepository':
    """获取 Research Repository"""
    if self._research is None:
        from .repositories import ResearchRepository
        self._research = ResearchRepository(self)
    return self._research

@property
def citations(self) -> 'CitationRepository':
    """获取 Citation Repository"""
    if self._citations is None:
        from .repositories import CitationRepository
        self._citations = CitationRepository(self)
    return self._citations
```

- [ ] **Step 3: 提交**

```bash
git add mkg/database.py
git commit -m "feat(db): integrate Repository pattern into Database class"
```

---

## Task 6: 添加向后兼容层

**Files:**
- Modify: `mkg/database.py`

- [ ] **Step 1: 添加向后兼容方法**

在 `Database` 类末尾添加委托方法：

```python
# ========== 向后兼容方法（委托给 Repository）==========

def add_paper(self, paper_data: dict) -> str:
    """向后兼容：使用 papers.add()"""
    return self.papers.add(paper_data)

def get_paper(self, identifier: str) -> Optional[dict]:
    """向后兼容：使用 papers.get()"""
    return self.papers.get(identifier)

def get_all_papers(self) -> list:
    """向后兼容：使用 papers.get_all()"""
    return self.papers.get_all()

def get_papers_by_status(self, status: str) -> list:
    """向后兼容：使用 papers.get_by_status()"""
    return self.papers.get_by_status(status)

def get_papers_by_folder(self, folder_id: str) -> list:
    """向后兼容：使用 papers.get_by_folder()"""
    return self.papers.get_by_folder(folder_id)

def update_paper_status(self, doi: str, status: str, error_message: str = None):
    """向后兼容：使用 papers.update_status()"""
    return self.papers.update_status(doi, status, error_message)

def add_pdf_path(self, doi: str, pdf_path: str):
    """向后兼容：使用 papers.add_pdf_path()"""
    return self.papers.add_pdf_path(doi, pdf_path)

def move_paper_to_folder(self, doi: str, folder_id: str):
    """向后兼容：使用 papers.move_to_folder()"""
    return self.papers.move_to_folder(doi, folder_id)

# Concept 方法
def add_concept(self, concept_data: dict) -> str:
    return self.concepts.add(concept_data)

def get_concept(self, concept_id: str) -> Optional[dict]:
    return self.concepts.get(concept_id)

def get_concept_by_text(self, text: str) -> Optional[dict]:
    return self.concepts.get_by_text(text)

def get_all_concepts(self) -> list:
    return self.concepts.get_all()

def get_root_concepts(self) -> list:
    return self.concepts.get_root()

def get_concept_children(self, concept_id: str) -> list:
    return self.concepts.get_children(concept_id)

def get_concept_parents(self, concept_id: str) -> list:
    return self.concepts.get_parents(concept_id)

def get_concept_tree(self, root_id: str = None) -> dict:
    return self.concepts.get_tree(root_id)

def get_papers_by_concept(self, concept_id: str) -> list:
    return self.concepts.get_papers(concept_id)

def get_concepts_by_paper(self, paper_doi: str) -> list:
    return self.papers.get_concepts(paper_doi)

def add_concept_relation(self, parent_id: str, child_id: str, relation_type: str = "parent-child"):
    return self.concepts.add_relation(parent_id, child_id, relation_type)

# Folder 方法
def get_all_folders(self) -> list:
    return self.folders.get_all()

def get_folder(self, folder_id: str) -> Optional[dict]:
    return self.folders.get(folder_id)

def create_folder(self, folder_data: dict) -> str:
    return self.folders.create(folder_data.get('name'), folder_data.get('description'))

def update_folder(self, folder_id: str, data: dict):
    return self.folders.update(folder_id, data.get('name'), data.get('description'))

def delete_folder(self, folder_id: str, delete_contents: bool = True) -> bool:
    return self.folders.delete(folder_id)

def ensure_default_folder(self):
    return self.folders.ensure_default()

# LLM Config 方法
def get_llm_config(self) -> Optional[Dict]:
    return self.config.get_llm_config()

def save_llm_config(self, mode: str, providers: List[Dict]) -> Dict:
    return self.config.save_llm_config(mode, providers)

def get_llm_provider_for_function(self, function_group: str) -> Optional[Dict]:
    return self.config.get_llm_provider_for_function(function_group)

def get_active_llm_provider(self) -> Optional[Dict]:
    return self.config.get_active_llm_provider()

# S2 Config 方法
def get_s2_config(self) -> Optional[Dict]:
    return self.config.get_s2_config()

def save_s2_config(self, api_key: str, enabled: bool = True) -> Dict:
    return self.config.save_s2_config(api_key, enabled)

# Conversation 方法
def create_conversation(self, device_id: str) -> str:
    return self.conversations.create(device_id)

def get_conversation(self, conv_id: str) -> Optional[dict]:
    return self.conversations.get(conv_id)

def get_conversations(self, device_id: str, limit: int = 50) -> List[Dict]:
    return self.conversations.get_all(device_id, limit)

def update_conversation_title(self, conv_id: str, title: str):
    return self.conversations.update_title(conv_id, title)

def update_conversation_timestamp(self, conv_id: str):
    return self.conversations.update_timestamp(conv_id)

def delete_conversation(self, conv_id: str):
    return self.conversations.delete(conv_id)

def add_message(self, conv_id: str, role: str, content: str, 
               agent: Optional[str] = None, attachments: Optional[List] = None):
    return self.conversations.add_message(conv_id, role, content, agent, attachments)

def get_messages(self, conv_id: str) -> List[Dict]:
    return self.conversations.get_messages(conv_id)

# Research 方法
def create_research_session(self, session_id: str, target_type: str, target_id: str, query: str):
    return self.research.create_session(session_id, target_type, target_id, query)

def get_research_session(self, session_id: str) -> Optional[Dict]:
    return self.research.get_session(session_id)

def update_research_progress(self, session_id: str, progress: int, dimensions: List[str]):
    return self.research.update_progress(session_id, progress, dimensions)

def save_research_finding(self, session_id: str, dimension: str, finding: str, confidence: float = None):
    return self.research.save_finding(session_id, dimension, finding, confidence)

def get_research_findings(self, session_id: str) -> List[Dict]:
    return self.research.get_findings(session_id)

def save_research_report(self, session_id: str, report: str):
    return self.research.save_report(session_id, report)

# Citation 方法
def add_paper_citation(self, data: Dict):
    return self.citations.add(data.get('paper_doi'), data)

def get_paper_citations(self, paper_id: str) -> List[Dict]:
    return self.citations.get_paper_citations(paper_id)

def get_paper_cited_by(self, paper_id: str) -> List[Dict]:
    return self.citations.get_paper_cited_by(paper_id)

def get_internal_citation_edges(self) -> List[Dict]:
    return self.citations.get_internal_edges()

def get_all_citations(self) -> List[Dict]:
    return self.citations.get_all()

def clear_paper_citations(self, paper_id: str = None):
    return self.citations.clear_paper_citations(paper_id)
```

- [ ] **Step 2: 提交**

```bash
git add mkg/database.py
git commit -m "feat(db): add backward compatibility layer for all Database methods"
```

---

## Task 7: 创建基础测试

**Files:**
- Create: `tests/repositories/__init__.py`
- Create: `tests/repositories/test_paper_repo.py`
- Create: `tests/repositories/test_concept_repo.py`

- [ ] **Step 1: 创建 `tests/repositories/__init__.py`**

```python
# tests/repositories/__init__.py
"""Repository tests"""
```

- [ ] **Step 2: 创建 `tests/repositories/test_paper_repo.py`**

```python
# tests/repositories/test_paper_repo.py
"""
PaperRepository tests
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mkg.database import Database
from mkg.repositories import PaperRepository


@pytest.fixture
def test_db():
    """创建测试数据库"""
    db = Database(":memory:")
    db.connect()
    yield db
    db.close()


def test_add_paper(test_db):
    """测试添加论文"""
    repo = test_db.papers
    doi = repo.add({
        "doi": "10.1234/test",
        "title": "Test Paper"
    })
    assert doi == "10.1234/test"

    paper = repo.get("10.1234/test")
    assert paper is not None
    assert paper["title"] == "Test Paper"


def test_get_paper_by_s2_id(test_db):
    """测试通过 S2 ID 获取论文"""
    repo = test_db.papers
    repo.add({
        "doi": "10.1234/s2test",
        "title": "S2 Test Paper",
        "s2_paper_id": "abc123"
    })

    paper = repo.get_by_s2_id("abc123")
    assert paper is not None
    assert paper["title"] == "S2 Test Paper"


def test_update_status(test_db):
    """测试更新论文状态"""
    repo = test_db.papers
    repo.add({"doi": "10.1234/status", "title": "Status Test"})
    
    repo.update_status("10.1234/status", "processed")
    
    paper = repo.get("10.1234/status")
    assert paper["status"] == "processed"


def test_move_to_folder(test_db):
    """测试移动论文到文件夹"""
    repo = test_db.papers
    folder_repo = test_db.folders
    
    folder_id = folder_repo.create("Test Folder")
    repo.add({"doi": "10.1234/folder", "title": "Folder Test"})
    
    repo.move_to_folder("10.1234/folder", folder_id)
    
    papers = repo.get_by_folder(folder_id)
    assert len(papers) == 1
    assert papers[0]["title"] == "Folder Test"


def test_backward_compatibility(test_db):
    """测试向后兼容方法"""
    # 使用旧的 Database 方法
    doi = test_db.add_paper({"doi": "10.1234/compat", "title": "Compat Test"})
    assert doi == "10.1234/compat"
    
    paper = test_db.get_paper("10.1234/compat")
    assert paper["title"] == "Compat Test"
```

- [ ] **Step 3: 创建 `tests/repositories/test_concept_repo.py`**

```python
# tests/repositories/test_concept_repo.py
"""
ConceptRepository tests
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mkg.database import Database


@pytest.fixture
def test_db():
    """创建测试数据库"""
    db = Database(":memory:")
    db.connect()
    yield db
    db.close()


def test_add_concept(test_db):
    """测试添加概念"""
    repo = test_db.concepts
    concept_id = repo.add({"text": "Machine Learning"})
    
    assert concept_id == "machine-learning"
    
    concept = repo.get("machine-learning")
    assert concept is not None
    assert concept["text"] == "Machine Learning"


def test_concept_hierarchy(test_db):
    """测试概念层级关系"""
    repo = test_db.concepts
    
    # 添加父子概念
    repo.add({"text": "AI"})
    repo.add({"text": "Machine Learning"})
    repo.add({"text": "Deep Learning"})
    
    # 建立关系
    repo.add_relation("ai", "machine-learning")
    repo.add_relation("machine-learning", "deep-learning")
    
    # 测试获取子概念
    children = repo.get_children("ai")
    assert len(children) == 1
    assert children[0]["text"] == "Machine Learning"
    
    # 测试获取父概念
    parents = repo.get_parents("deep-learning")
    assert len(parents) == 1
    assert parents[0]["text"] == "Machine Learning"


def test_root_concepts(test_db):
    """测试根概念"""
    repo = test_db.concepts
    
    repo.add({"text": "Root Concept"})
    repo.add({"text": "Child Concept"})
    repo.add_relation("root-concept", "child-concept")
    
    roots = repo.get_root()
    root_ids = [r["id"] for r in roots]
    
    assert "root-concept" in root_ids
    assert "child-concept" not in root_ids


def test_backward_compatibility(test_db):
    """测试向后兼容方法"""
    concept_id = test_db.add_concept({"text": "Backward Compat"})
    assert concept_id == "backward-compat"
    
    concept = test_db.get_concept("backward-compat")
    assert concept["text"] == "Backward Compat"
```

- [ ] **Step 4: 运行测试**

```bash
cd D:/meta-knowledge-graph-main
python -m pytest tests/repositories/ -v
```

Expected: All tests pass

- [ ] **Step 5: 提交**

```bash
git add tests/repositories/
git commit -m "test(db): add basic tests for PaperRepository and ConceptRepository"
```

---

## Task 8: 最终验证

- [ ] **Step 1: 运行完整测试套件**

```bash
cd D:/meta-knowledge-graph-main
python -m pytest tests/ -v --tb=short
```

Expected: All tests pass

- [ ] **Step 2: 启动后端验证功能**

```bash
cd D:/meta-knowledge-graph-main
python -m uvicorn backend.main:app --reload --port 8000
```

Expected: Server starts without errors

- [ ] **Step 3: 提交最终变更**

```bash
git add -A
git commit -m "refactor(db): complete Database.py split into Repository pattern

- Create 7 Repository classes: Paper, Concept, Folder, Config, 
  Conversation, Research, Citation
- Add BaseRepository with common utilities
- Add backward compatibility layer in Database class
- Add unit tests for PaperRepository and ConceptRepository

Closes: #database-refactoring"
```

---

## 预期结果

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| `database.py` 行数 | 2146 | ~200 |
| 最大类方法数 | 97 | ~20 |
| 可独立测试 | ❌ | ✅ |
| 职责清晰度 | 低 | 高 |