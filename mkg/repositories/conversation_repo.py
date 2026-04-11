# mkg/repositories/conversation_repo.py
"""
ConversationRepository - 会话相关数据库操作
"""

import uuid

from .base import BaseRepository


class ConversationRepository(BaseRepository):
    """会话数据访问层"""

    # ========== 会话 CRUD ==========

    def create(self, device_id: str) -> str:
        """
        创建会话

        Args:
            device_id: 设备标识

        Returns:
            会话 ID (UUID)
        """
        conv_id = str(uuid.uuid4())

        self.execute_write("""
            INSERT INTO conversations (id, device_id)
            VALUES (?, ?)
        """, (conv_id, device_id))

        return conv_id

    def get(self, conv_id: str) -> dict | None:
        """
        获取会话

        Args:
            conv_id: 会话 ID

        Returns:
            会话字典，或 None
        """
        cursor = self.execute_read(
            "SELECT * FROM conversations WHERE id = ?",
            (conv_id,)
        )
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_all(self, device_id: str, limit: int = 50) -> list[dict]:
        """
        获取设备的所有会话

        Args:
            device_id: 设备标识
            limit: 返回数量限制

        Returns:
            会话列表
        """
        cursor = self.execute_read("""
            SELECT * FROM conversations
            WHERE device_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
        """, (device_id, limit))

        return [dict(row) for row in cursor.fetchall()]

    def update_title(self, conv_id: str, title: str) -> bool:
        """
        更新会话标题

        Args:
            conv_id: 会话 ID
            title: 新标题

        Returns:
            是否更新成功
        """
        self.execute_write("""
            UPDATE conversations
            SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (title, conv_id))

        return True

    def update_timestamp(self, conv_id: str) -> bool:
        """
        更新会话时间戳

        Args:
            conv_id: 会话 ID

        Returns:
            是否更新成功
        """
        self.execute_write("""
            UPDATE conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (conv_id,))

        return True

    def delete(self, conv_id: str) -> bool:
        """
        删除会话及消息

        Args:
            conv_id: 会话 ID

        Returns:
            是否删除成功
        """
        # 由于有 ON DELETE CASCADE，消息会自动删除
        self.execute_write(
            "DELETE FROM conversations WHERE id = ?",
            (conv_id,)
        )

        return True

    # ========== 消息 CRUD ==========

    def get_messages(self, conv_id: str) -> list[dict]:
        """
        获取会话的所有消息

        Args:
            conv_id: 会话 ID

        Returns:
            消息列表
        """
        cursor = self.execute_read("""
            SELECT * FROM conversation_messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
        """, (conv_id,))

        messages = []
        for row in cursor.fetchall():
            msg = dict(row)
            # 解析 attachments JSON
            msg['attachments'] = self._deserialize_json(msg.get('attachments'), [])
            messages.append(msg)

        return messages

    def add_message(self, conv_id: str, role: str, content: str,
                    agent: str = None, attachments: list[dict] = None) -> str:
        """
        添加消息

        Args:
            conv_id: 会话 ID
            role: 角色（user/assistant）
            content: 消息内容
            agent: Agent 名称（可选，用于 assistant 消息）
            attachments: 附件列表（可选）

        Returns:
            消息 ID (UUID)
        """
        msg_id = str(uuid.uuid4())

        self.execute_write("""
            INSERT INTO conversation_messages
                (id, conversation_id, role, content, agent, attachments)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            msg_id,
            conv_id,
            role,
            content,
            agent,
            self._serialize_json(attachments) if attachments else None
        ))

        # 更新会话时间戳
        self.update_timestamp(conv_id)

        return msg_id

    def get_message(self, msg_id: str) -> dict | None:
        """
        获取单条消息

        Args:
            msg_id: 消息 ID

        Returns:
            消息字典，或 None
        """
        cursor = self.execute_read(
            "SELECT * FROM conversation_messages WHERE id = ?",
            (msg_id,)
        )
        row = cursor.fetchone()

        if row:
            msg = dict(row)
            msg['attachments'] = self._deserialize_json(msg.get('attachments'), [])
            return msg

        return None

    def delete_message(self, msg_id: str) -> bool:
        """
        删除消息

        Args:
            msg_id: 消息 ID

        Returns:
            是否删除成功
        """
        self.execute_write(
            "DELETE FROM conversation_messages WHERE id = ?",
            (msg_id,)
        )

        return True
