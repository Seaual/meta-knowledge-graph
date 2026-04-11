# mkg/repositories/__init__.py
"""
Repository 模块 - 数据访问层

每个 Repository 负责一个领域的数据库操作
"""

from .base import BaseRepository
from .citation_repo import CitationRepository
from .concept_repo import ConceptRepository
from .config_repo import ConfigRepository
from .conversation_repo import ConversationRepository
from .folder_repo import FolderRepository
from .paper_repo import PaperRepository
from .research_repo import ResearchRepository

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
