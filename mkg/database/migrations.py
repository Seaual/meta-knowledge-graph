# mkg/database/migrations.py
"""Database migrations"""

class MigrationMixin:
    """Migration management mixin"""


    def _migrate_memory_tables(self):
        """为 Memory 模块迁移新字段到现有表（幂等）"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("ALTER TABLE conversations ADD COLUMN context_summary TEXT")
        except Exception:
            pass  # 字段已存在
