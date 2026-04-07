# Database.py 拆分重构设计

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 God Class `Database` 拆分为多个职责单一的 Repository 类，提高可维护性和可测试性。

**Architecture:** Repository 模式 - 每个领域一个 Repository 类，共享 Database 连接管理器。

**Tech Stack:** Python 3.10+, SQLite, 现有代码结构

---

## 问题分析

当前 `mkg/database.py` 存在以下问题：
- **God Class**: 97 个方法，2146 行代码
- **职责过多**: 涵盖 Paper、Concept、Folder、LLM Config、S2、Conversation、Research、Citation 等 8+ 个领域
- **难以测试**: 无法单独测试某个领域的逻辑
- **难以维护**: 修改一个领域可能影响其他领域

## 解决方案

### 架构概览

```
mkg/
├── database.py          # 保留：连接管理器 + 表初始化
└── repositories/        # 新建：各领域 Repository
    ├── __init__.py
    ├── paper_repo.py    # Paper 相关操作 (~18 方法)
    ├── concept_repo.py  # Concept 相关操作 (~20 方法)
    ├── folder_repo.py   # Folder 相关操作 (~5 方法)
    ├── config_repo.py   # LLM/S2 配置 (~6 方法)
    ├── conversation_repo.py  # 会话管理 (~8 方法)
    ├── research_repo.py # 研究会话 (~8 方法)
    └── citation_repo.py # 引用关系 (~8 方法)
```

### Database 类改造

**保留职责：**
- 连接管理 (`connect`, `close`, `get_cursor`)
- 表结构初始化 (`_init_tables`)
- 基础 CRUD 工具 (`execute_write`, `execute_read`)
- Repository 实例管理

**移除：** 所有业务方法迁移到对应 Repository

### Repository 接口设计

#### PaperRepository

```python
# mkg/repositories/paper_repo.py
class PaperRepository:
    def __init__(self, db: Database):
        self._db = db
    
    # CRUD
    def add(self, paper_data: dict) -> str
    def get(self, identifier: str) -> Optional[dict]
    def get_all(self, folder_id: str = None) -> list
    def get_all_basic(self) -> list
    def get_by_status(self, status: str) -> list
    def update_status(self, doi: str, status: str, error_message: str = None)
    def update_metadata(self, doi: str, metadata: dict)
    def delete(self, doi: str)
    
    # 文件管理
    def add_pdf_path(self, doi: str, pdf_path: str)
    
    # 文件夹关联
    def get_by_folder(self, folder_id: str) -> list
    def move_to_folder(self, doi: str, folder_id: str)
    
    # S2 集成
    def get_by_s2_id(self, s2_paper_id: str) -> Optional[dict]
    def get_all_with_s2_id(self) -> list
    def update_s2_metadata(self, doi: str, metadata: dict)
    
    # 概念关联
    def get_by_concept(self, concept_id: str) -> list
    def get_concepts(self, paper_doi: str) -> list
    def get_contribution(self, doi: str) -> dict
    
    # 概念提取
    def get_extraction(self, doi: str) -> Optional[dict]
    def save_extraction(self, paper_doi: str, hierarchy: dict, raw_response: str)
    def migrate_concepts(self, paper_doi: str, new_concepts: list)
    
    # 处理日志
    def log_processing(self, doi: str, stage: str, status: str, message: str = None)
```

#### ConceptRepository

```python
# mkg/repositories/concept_repo.py
class ConceptRepository:
    def __init__(self, db: Database):
        self._db = db
    
    # CRUD
    def add(self, concept_data: dict) -> str
    def get(self, concept_id: str) -> Optional[dict]
    def get_by_text(self, text: str) -> Optional[dict]
    def get_all(self) -> list
    def get_root(self) -> list
    def get_count(self) -> int
    def delete(self, concept_id: str)
    
    # 层级关系
    def get_children(self, concept_id: str) -> list
    def get_parents(self, concept_id: str) -> list
    def get_tree(self, root_id: str = None) -> dict
    def add_relation(self, parent_id: str, child_id: str, relation_type: str = "parent-child")
    def update_relations(self, concept_id: str, parent_ids: list, child_ids: list)
    
    # 分类
    def get_by_category(self, category: str) -> list
    def get_by_category_and_folder(self, category: str, folder_id: str) -> list
    def get_by_folder(self, folder_id: str) -> list
    def get_relations_by_folder(self, folder_id: str) -> list
    
    # 论文关联
    def get_papers(self, concept_id: str) -> list
    def add_paper_concept(self, paper_doi: str, concept_id: str, relevance: float = 1.0)
    
    # 深度缓存
    def recalculate_depth_cache(self)
    
    # 内部方法
    def _delete_orphaned(self, concept_id: str)
    def _to_slug(self, text: str) -> str
```

#### FolderRepository

```python
# mkg/repositories/folder_repo.py
class FolderRepository:
    def __init__(self, db: Database):
        self._db = db
    
    def create(self, name: str, description: str = None) -> str
    def get(self, folder_id: str) -> Optional[dict]
    def get_all(self) -> list
    def update(self, folder_id: str, name: str = None, description: str = None)
    def delete(self, folder_id: str)
    def ensure_default(self) -> str
```

#### ConfigRepository

```python
# mkg/repositories/config_repo.py
class ConfigRepository:
    def __init__(self, db: Database):
        self._db = db
    
    # LLM 配置
    def get_llm_config(self) -> dict
    def save_llm_config(self, config: dict)
    def get_llm_provider_for_function(self, function_group: str) -> Optional[dict]
    def get_active_llm_provider(self, function_group: str = None) -> Optional[dict]
    
    # S2 配置
    def get_s2_config(self) -> dict
    def save_s2_config(self, api_key: str, enabled: bool = True)
```

#### ConversationRepository

```python
# mkg/repositories/conversation_repo.py
class ConversationRepository:
    def __init__(self, db: Database):
        self._db = db
    
    def create(self, device_id: str) -> str
    def get(self, conversation_id: str) -> Optional[dict]
    def get_all(self, device_id: str) -> list
    def update_title(self, conversation_id: str, title: str)
    def update_timestamp(self, conversation_id: str)
    def delete(self, conversation_id: str)
    
    # 消息
    def get_messages(self, conversation_id: str) -> list
    def add_message(self, conversation_id: str, role: str, content: str, agent: str = None, attachments: list = None)
```

#### ResearchRepository

```python
# mkg/repositories/research_repo.py
class ResearchRepository:
    def __init__(self, db: Database):
        self._db = db
    
    def create_session(self, target_type: str, target_id: str, query: str) -> str
    def get_session(self, session_id: str) -> Optional[dict]
    def update_progress(self, session_id: str, progress: int, dimensions: list)
    def save_finding(self, session_id: str, dimension: str, finding: str)
    def get_findings(self, session_id: str) -> dict
    def save_report(self, session_id: str, report: str)
    
    # S2 推荐
    def add_s2_recommendation(self, concept_id: str, paper_id: str, paper_data: dict)
    def get_s2_recommendations(self, concept_id: str) -> list
    def clear_s2_recommendations(self, concept_id: str)
```

#### CitationRepository

```python
# mkg/repositories/citation_repo.py
class CitationRepository:
    def __init__(self, db: Database):
        self._db = db
    
    def add(self, paper_doi: str, citation_data: dict)
    def get_all(self) -> list
    def get_by_s2_id(self, s2_paper_id: str) -> Optional[dict]
    def get_paper_citations(self, paper_doi: str) -> list
    def get_paper_cited_by(self, paper_doi: str) -> list
    def get_internal_edges(self) -> list
    def clear_paper_citations(self, paper_doi: str)
```

### 向后兼容

保留原 Database 方法签名，内部委托给 Repository：

```python
# mkg/database.py
import warnings
from .repositories import (
    PaperRepository, ConceptRepository, FolderRepository,
    ConfigRepository, ConversationRepository, ResearchRepository,
    CitationRepository
)

class Database:
    def __init__(self, db_path: str = "mkg.db"):
        self._conn = None
        self._db_path = db_path
        
        # 初始化 repositories
        self.papers = PaperRepository(self)
        self.concepts = ConceptRepository(self)
        self.folders = FolderRepository(self)
        self.config = ConfigRepository(self)
        self.conversations = ConversationRepository(self)
        self.research = ResearchRepository(self)
        self.citations = CitationRepository(self)
    
    # 向后兼容方法
    def add_paper(self, paper_data: dict) -> str:
        warnings.warn("Use db.papers.add() instead", DeprecationWarning)
        return self.papers.add(paper_data)
    
    # ... 其他向后兼容方法
```

### 迁移策略

1. **Phase 1**: 创建 repositories 目录和各 Repository 类
2. **Phase 2**: 将 Database 中的方法迁移到对应 Repository
3. **Phase 3**: 在 Database 中添加向后兼容的委托方法
4. **Phase 4**: 更新所有调用方使用新 API
5. **Phase 5**: 移除向后兼容方法（可选，后续版本）

## 测试策略

每个 Repository 独立测试：

```python
# tests/repositories/test_paper_repo.py
import pytest
from mkg.database import Database
from mkg.repositories import PaperRepository

@pytest.fixture
def test_db():
    db = Database(":memory:")
    db.connect()
    yield db
    db.close()

def test_add_paper(test_db):
    repo = test_db.papers
    doi = repo.add({"title": "Test Paper", "doi": "10.1234/test"})
    assert doi == "10.1234/test"
    
    paper = repo.get("10.1234/test")
    assert paper["title"] == "Test Paper"

def test_get_by_folder(test_db):
    repo = test_db.papers
    folder_repo = test_db.folders
    
    folder_id = folder_repo.create("Test Folder")
    repo.add({"title": "Paper 1", "doi": "10.1/1", "folder_id": folder_id})
    repo.add({"title": "Paper 2", "doi": "10.1/2"})
    
    papers = repo.get_by_folder(folder_id)
    assert len(papers) == 1
    assert papers[0]["title"] == "Paper 1"
```

## 预期收益

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| 单文件最大行数 | 2146 | ~300 |
| 单类最大方法数 | 97 | ~20 |
| 可独立测试 | ❌ | ✅ |
| 职责清晰度 | 低 | 高 |
| 新功能添加复杂度 | 高 | 低 |

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 破坏现有代码 | 向后兼容层 + 全面测试 |
| 性能影响 | 共享连接，无额外开销 |
| 迁移遗漏 | 渐进迁移，保留旧方法 |