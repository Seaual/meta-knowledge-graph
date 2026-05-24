# mkg/database/core.py
"""Database core - connection, transactions, encryption, repositories"""

"""
SQLite 数据库管理 - 论文、概念、动态层级关系存储

新设计：
- concepts 表：存储概念（原 keywords），移除固定 level 字段
- concept_relations 表：存储父子概念关系（动态层级）
- paper_concepts 表：论文 - 概念多对多关联
"""

import base64
import getpass
import hashlib
import json
import platform
import sqlite3
import threading
import uuid
from pathlib import Path

from cryptography.fernet import Fernet


def _derive_encryption_key() -> bytes:
    """基于本地设备信息派生加密密钥"""
    salt = b"mkg-local-storage-salt-v1"
    device_info = f"{platform.node()}-{getpass.getuser()}".encode("utf-8")
    key = hashlib.pbkdf2_hmac("sha256", device_info, salt, iterations=100000, dklen=32)
    return base64.urlsafe_b64encode(key)


class DatabaseCore:
    """SQLite 数据库管理类"""

    def __init__(self, db_path: str = "mkg.db"):
        self.db_path = Path(db_path)
        self.conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()
        self._fernet = Fernet(_derive_encryption_key())

        # Repository 实例（延迟初始化）
        self._papers = None
        self._concepts = None
        self._folders = None
        self._config = None
        self._conversations = None
        self._research = None
        self._citations = None
        self._neo4j_store = None  # Neo4j 存储（延迟初始化）

    def connect(self):
        """连接到数据库"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # 启用 WAL 模式以支持并发读写
        self.conn.execute("PRAGMA journal_mode=WAL")
        # 设置繁忙超时为 30 秒
        self.conn.execute("PRAGMA busy_timeout=30000")
        # 设置外键约束
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_tables()
        self._migrate_memory_tables()
        self.ensure_default_folder()  # 确保默认文件夹存在

    def _encrypt_value(self, value: str | None) -> str | None:
        """加密敏感值（API Key 等）"""
        if not value:
            return value
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def _decrypt_value(self, value: str | None) -> str | None:
        """解密敏感值，兼容明文存储的旧数据"""
        if not value:
            return value
        try:
            return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except Exception:
            # 解密失败，可能是旧数据的明文，直接返回原值
            return value

    def get_cursor(self):
        """获取数据库游标（线程安全）"""
        with self._lock:
            return self.conn.cursor()

    def execute_write(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行写操作（线程安全）"""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor

    def execute_read(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行读操作（线程安全）"""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor

    def close(self):
        """关闭连接"""
        if self._neo4j_store:
            self._neo4j_store.close()
            self._neo4j_store = None
        if self.conn:
            self.conn.close()
            self.conn = None

    # ========== Repository 属性访问器 ==========

    @property
    def papers(self) -> "PaperRepository":
        """获取 Paper Repository"""
        if self._papers is None:
            from ..repositories import PaperRepository

            self._papers = PaperRepository(self)
        return self._papers

    @property
    def concepts(self) -> "ConceptRepository":
        """获取 Concept Repository"""
        if self._concepts is None:
            from ..repositories import ConceptRepository

            self._concepts = ConceptRepository(self)
        return self._concepts

    @property
    def folders(self) -> "FolderRepository":
        """获取 Folder Repository"""
        if self._folders is None:
            from ..repositories import FolderRepository

            self._folders = FolderRepository(self)
        return self._folders

    @property
    def config(self) -> "ConfigRepository":
        """获取 Config Repository"""
        if self._config is None:
            from ..repositories import ConfigRepository

            self._config = ConfigRepository(self)
        return self._config

    @property
    def conversations(self) -> "ConversationRepository":
        """获取 Conversation Repository"""
        if self._conversations is None:
            from ..repositories import ConversationRepository

            self._conversations = ConversationRepository(self)
        return self._conversations

    @property
    def research(self) -> "ResearchRepository":
        """获取 Research Repository"""
        if self._research is None:
            from ..repositories import ResearchRepository

            self._research = ResearchRepository(self)
        return self._research

    @property
    def citations(self) -> "CitationRepository":
        """获取 Citation Repository"""
        if self._citations is None:
            from ..repositories import CitationRepository

            self._citations = CitationRepository(self)
        return self._citations

    @property
    def neo4j_store(self) -> "Neo4jStore | None":
        """获取 Neo4j 存储（延迟初始化，如果启用）"""
        if self._neo4j_store is None:
            import os

            if os.getenv("USE_NEO4J", "").lower() in ("true", "1", "yes"):
                from ..neo4j_store import Neo4jStore

                self._neo4j_store = Neo4jStore()
        return self._neo4j_store
    # ========== 上下文管理器 ==========

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __getattr__(self, name: str):
        """向后兼容: 将 Database 方法转发到 Repository"""
        for repo_attr in ("papers", "concepts", "folders", "config", "conversations", "research", "citations"):
            repo = getattr(self, repo_attr)
            if hasattr(repo, name):
                return getattr(repo, name)
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")
