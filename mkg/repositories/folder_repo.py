# mkg/repositories/folder_repo.py
"""
FolderRepository - 文件夹相关数据库操作
"""

from typing import Optional, List
from .base import BaseRepository


class FolderRepository(BaseRepository):
    """文件夹数据访问层"""

    def create(self, name: str, description: str = None) -> str:
        """
        创建文件夹

        Args:
            name: 文件夹名称
            description: 文件夹描述（可选）

        Returns:
            folder_id
        """
        # 生成 folder_id（基于名称的 slug）
        folder_id = self._to_slug(name)

        self.execute_write("""
            INSERT INTO folders (id, name, description)
            VALUES (?, ?, ?)
        """, (folder_id, name, description))

        return folder_id

    def get(self, folder_id: str) -> Optional[dict]:
        """
        获取文件夹

        Args:
            folder_id: 文件夹 ID

        Returns:
            文件夹字典，或 None
        """
        cursor = self.execute_read(
            "SELECT * FROM folders WHERE id = ?",
            (folder_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_all(self) -> List[dict]:
        """
        获取所有文件夹

        Returns:
            文件夹列表
        """
        cursor = self.execute_read(
            "SELECT * FROM folders ORDER BY created_at ASC"
        )
        return [dict(row) for row in cursor.fetchall()]

    def update(self, folder_id: str, name: str = None, description: str = None) -> bool:
        """
        更新文件夹

        Args:
            folder_id: 文件夹 ID
            name: 新名称（可选）
            description: 新描述（可选）

        Returns:
            是否更新成功
        """
        # 不能更新 default 文件夹的名称
        if folder_id == 'default' and name:
            return False

        updates = []
        params = []

        if name:
            updates.append("name = ?")
            params.append(name)
        if description:
            updates.append("description = ?")
            params.append(description)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(folder_id)

        query = "UPDATE folders SET " + ", ".join(updates) + " WHERE id = ?"
        self.execute_write(query, tuple(params))

        return True

    def delete(self, folder_id: str) -> bool:
        """
        删除文件夹（不能删除 default）

        Args:
            folder_id: 文件夹 ID

        Returns:
            是否删除成功

        Note:
            删除文件夹时，其中的论文会移动到 default 文件夹
        """
        # 不能删除 default 文件夹
        if folder_id == 'default':
            return False

        # 将该文件夹中的论文移动到 default
        self.execute_write(
            "UPDATE papers SET folder_id = 'default' WHERE folder_id = ?",
            (folder_id,)
        )

        # 删除文件夹
        self.execute_write(
            "DELETE FROM folders WHERE id = ?",
            (folder_id,)
        )

        return True

    def ensure_default(self) -> str:
        """
        确保默认文件夹存在

        Returns:
            default 文件夹 ID
        """
        cursor = self.execute_read(
            "SELECT id FROM folders WHERE id = 'default'"
        )
        row = cursor.fetchone()

        if not row:
            self.execute_write("""
                INSERT INTO folders (id, name, description)
                VALUES ('default', 'Default', 'Default folder for papers')
            """)

        return 'default'

    def update_paper_count(self, folder_id: str) -> None:
        """
        更新文件夹的论文计数

        Args:
            folder_id: 文件夹 ID
        """
        self.execute_write("""
            UPDATE folders SET paper_count = (
                SELECT COUNT(*) FROM papers WHERE folder_id = ?
            ) WHERE id = ?
        """, (folder_id, folder_id))

    def _to_slug(self, text: str) -> str:
        """
        将文本转换为 slug ID

        Args:
            text: 文件夹名称

        Returns:
            slug ID（小写，连字符分隔）
        """
        import re
        slug = text.lower()
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        slug = slug.strip('-')
        return slug or 'folder'