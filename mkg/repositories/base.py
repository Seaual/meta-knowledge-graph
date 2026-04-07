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