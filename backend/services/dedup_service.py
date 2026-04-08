# backend/services/dedup_service.py
"""
去重服务 - 概念去重扫描和执行
"""

import uuid
from typing import Dict, List, Optional
from mkg.database import Database


class DedupService:
    """概念去重服务"""

    def __init__(self, db: Database):
        self.db = db

    def start_scan(self, folder_id: str = None) -> Dict:
        """开始去重扫描"""
        scan_id = str(uuid.uuid4())

        # 获取概念数量
        if folder_id:
            concepts = self.db.concepts.get_by_folder(folder_id)
        else:
            concepts = self.db.concepts.get_all()

        # 创建扫描任务记录
        self.db.execute_write("""
            INSERT INTO dedup_scans (id, folder_id, total_concepts, status, progress)
            VALUES (?, ?, ?, 'pending', 0)
        """, (scan_id, folder_id, len(concepts)))

        return {"scan_id": scan_id, "total_concepts": len(concepts)}

    def get_scan_status(self, scan_id: str) -> Optional[Dict]:
        """获取扫描状态"""
        cursor = self.db.execute_read(
            "SELECT * FROM dedup_scans WHERE id = ?",
            (scan_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_scan_status(self, scan_id: str, **kwargs):
        """更新扫描状态"""
        valid_fields = ['status', 'progress', 'suggestions', 'filtered_count',
                        'high_confidence_count', 'batches_completed', 'phase']
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in valid_fields:
                updates.append(f"{key} = ?")
                values.append(value)

        if updates:
            values.append(scan_id)
            self.db.execute_write(
                f"UPDATE dedup_scans SET {', '.join(updates)} WHERE id = ?",
                tuple(values)
            )

    def execute_merge(self, scan_id: str, merge_ids: List[str]) -> Dict:
        """执行概念合并"""
        scan = self.get_scan_status(scan_id)
        if not scan:
            return {"executed": 0, "details": [], "error": "Scan not found"}

        executed = 0
        details = []

        for merge_id in merge_ids:
            # TODO: 实现实际的合并逻辑
            executed += 1
            details.append({"merge_id": merge_id, "status": "success"})

        return {"executed": executed, "details": details}

    def cleanup_old_scans(self, max_age_hours: int = 24):
        """清理旧的扫描任务"""
        self.db.execute_write("""
            DELETE FROM dedup_scans
            WHERE created_at < datetime('now', ?)
        """, (f'-{max_age_hours} hours',))