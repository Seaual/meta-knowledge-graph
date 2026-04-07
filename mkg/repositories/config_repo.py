# mkg/repositories/config_repo.py
"""
ConfigRepository - 配置相关数据库操作
"""

from typing import Optional, Dict, List, Any
from .base import BaseRepository


class ConfigRepository(BaseRepository):
    """配置数据访问层"""

    # ========== LLM 配置 ==========

    def get_llm_config(self) -> Optional[dict]:
        """
        获取 LLM 配置

        Returns:
            LLM 配置字典，包含 mode 和 providers，或 None
        """
        cursor = self.execute_read(
            "SELECT * FROM llm_config ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()

        if not row:
            return None

        config = dict(row)

        # 获取提供商配置
        cursor = self.execute_read(
            "SELECT * FROM llm_provider_config WHERE config_id = ?",
            (config['id'],)
        )
        providers = []
        for provider_row in cursor.fetchall():
            provider = dict(provider_row)
            providers.append(provider)

        config['providers'] = providers

        return config

    def save_llm_config(self, mode: str, providers: List[Dict]) -> None:
        """
        保存 LLM 配置

        Args:
            mode: 模式（single/multi）
            providers: 提供商配置列表
        """
        # 插入或更新 llm_config
        cursor = self.execute_read("SELECT id FROM llm_config LIMIT 1")
        existing = cursor.fetchone()

        if existing:
            config_id = existing['id']
            self.execute_write(
                "UPDATE llm_config SET mode = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (mode, config_id)
            )
            # 清除旧的提供商配置
            self.execute_write("DELETE FROM llm_provider_config WHERE config_id = ?", (config_id,))
        else:
            cursor = self.execute_write(
                "INSERT INTO llm_config (mode) VALUES (?)",
                (mode,)
            )
            config_id = cursor.lastrowid

        # 插入新的提供商配置
        for provider in providers:
            self.execute_write("""
                INSERT INTO llm_provider_config
                    (config_id, function_group, provider, api_key, base_url, model, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                config_id,
                provider.get('function_group'),
                provider.get('provider'),
                provider.get('api_key'),
                provider.get('base_url'),
                provider.get('model'),
                provider.get('is_active', True)
            ))

    def get_llm_provider_for_function(self, function_group: str) -> Optional[dict]:
        """
        获取指定功能的提供商

        Args:
            function_group: 功能组名称

        Returns:
            提供商配置字典，或 None
        """
        cursor = self.execute_read("""
            SELECT p.* FROM llm_provider_config p
            JOIN llm_config c ON p.config_id = c.id
            WHERE p.function_group = ? AND p.is_active = 1 AND c.mode = 'multi'
            ORDER BY c.id DESC LIMIT 1
        """, (function_group,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_active_llm_provider(self) -> Optional[dict]:
        """
        获取活跃提供商（单模式）

        Returns:
            活跃提供商配置字典，或 None
        """
        cursor = self.execute_read("""
            SELECT p.* FROM llm_provider_config p
            JOIN llm_config c ON p.config_id = c.id
            WHERE p.is_active = 1 AND c.mode = 'single'
            ORDER BY c.id DESC LIMIT 1
        """)
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    # ========== S2 配置 ==========

    def get_s2_config(self) -> Optional[dict]:
        """
        获取 Semantic Scholar 配置

        Returns:
            S2 配置字典，包含 api_key 和 enabled，或 None
        """
        cursor = self.execute_read(
            "SELECT * FROM s2_config WHERE id = 1"
        )
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def save_s2_config(self, api_key: str, enabled: bool = True) -> None:
        """
        保存 Semantic Scholar 配置

        Args:
            api_key: API Key
            enabled: 是否启用
        """
        # 使用 INSERT OR REPLACE 确保 id = 1
        self.execute_write("""
            INSERT OR REPLACE INTO s2_config (id, api_key, enabled)
            VALUES (1, ?, ?)
        """, (api_key, enabled))