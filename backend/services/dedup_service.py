# backend/services/dedup_service.py
"""
去重服务 - 概念去重扫描和执行
"""

import json
import threading
import time
import uuid

from mkg.database import Database


class DedupService:
    """概念去重服务"""

    def __init__(self, db: Database):
        self.db = db
        self._scans: dict[str, dict] = {}  # in-memory scan threads

    def start_scan(self, folder_id: str = None) -> dict:
        """开始去重扫描"""
        scan_id = str(uuid.uuid4())

        # 获取概念数量
        if folder_id:
            concepts = self.db.concepts.get_by_folder(folder_id)
        else:
            concepts = self.db.concepts.get_all()

        total = len(concepts)

        # 创建扫描任务记录
        self.db.execute_write("""
            INSERT INTO dedup_scans (id, folder_id, total_concepts, status, progress, phase)
            VALUES (?, ?, ?, 'running', 0, 'prefiltering')
        """, (scan_id, folder_id, total))

        # 在后台线程执行扫描
        thread = threading.Thread(
            target=self._run_scan,
            args=(scan_id, folder_id, total),
            daemon=True,
        )
        thread.start()
        self._scans[scan_id] = {"thread": thread}

        return {"scan_id": scan_id, "total_concepts": total}

    def _run_scan(self, scan_id: str, folder_id: str, total_concepts: int):
        """执行实际的扫描逻辑"""
        try:
            # === Phase 1: Prefiltering ===
            self._update(scan_id, phase="prefiltering", progress=0)
            concepts = self._get_concepts(folder_id)

            # 预筛选：按 category 分组，同类内两两比较
            from collections import defaultdict
            by_category = defaultdict(list)
            for c in concepts:
                cat = c.get("category") or "unknown"
                by_category[cat].append(c)

            # 生成候选对：同类别 + 文本相似度启发
            candidate_pairs = []
            for cat, cats_concepts in by_category.items():
                candidate_pairs.extend(self._find_candidates(cats_concepts))

            self._update(scan_id, filtered_count=len(candidate_pairs), progress=10)

            # === Phase 2: Analyzing ===
            self._update(scan_id, phase="analyzing")

            # 分批次处理
            BATCH_SIZE = 10
            batches = [candidate_pairs[i:i+BATCH_SIZE] for i in range(0, len(candidate_pairs), BATCH_SIZE)]
            self._update(scan_id, batches_total=len(batches), batches_completed=0)

            suggestions = []
            high_confidence = 0
            concepts_scanned = 0

            for batch_idx, batch in enumerate(batches):
                for pair in batch:
                    confidence = self._compute_confidence(pair)
                    if confidence >= 0.6:
                        suggestion = self._build_suggestion(pair, confidence)
                        suggestions.append(suggestion)
                        if confidence >= 0.9:
                            high_confidence += 1
                    concepts_scanned += 2

                self._update(
                    scan_id,
                    concepts_scanned=concepts_scanned,
                    batches_completed=batch_idx + 1,
                    progress=10 + (batch_idx + 1) / len(batches) * 85,
                    estimated_time=max(0, (len(batches) - batch_idx - 1) * 2),
                )

            # === Phase 3: Completed ===
            self._update(
                scan_id,
                phase="completed",
                status="completed",
                progress=100,
                concepts_scanned=concepts_scanned,
                high_confidence_count=high_confidence,
                suggestions=json.dumps(suggestions, ensure_ascii=False),
                estimated_time=0,
            )

        except Exception as e:
            self._update(
                scan_id,
                status="failed",
                phase="failed",
                error=str(e),
            )

    def _get_concepts(self, folder_id: str = None) -> list[dict]:
        """获取概念列表"""
        if folder_id:
            return self.db.concepts.get_by_folder(folder_id)
        return self.db.concepts.get_all()

    def _find_candidates(self, concepts: list[dict]) -> list[tuple[dict, dict]]:
        """在同类概念中找出可能的重复对"""
        candidates = []
        n = len(concepts)
        for i in range(n):
            for j in range(i + 1, n):
                a = concepts[i]
                b = concepts[j]
                # 文本相似度启发：长度接近或包含关系
                text_a = a.get("text", "").lower()
                text_b = b.get("text", "").lower()
                if text_a == text_b:
                    candidates.append((a, b))
                elif text_a in text_b or text_b in text_a:
                    candidates.append((a, b))
                elif self._text_similarity(text_a, text_b) > 0.7:
                    candidates.append((a, b))
        return candidates

    def _text_similarity(self, a: str, b: str) -> float:
        """简单的文本相似度（基于公共字符）"""
        if not a or not b:
            return 0
        set_a = set(a)
        set_b = set(b)
        if not set_a or not set_b:
            return 0
        return len(set_a & set_b) / len(set_a | set_b)

    def _compute_confidence(self, pair: tuple[dict, dict]) -> float:
        """计算重复对的可信度"""
        a, b = pair
        text_a = a.get("text", "").lower()
        text_b = b.get("text", "").lower()

        # 完全匹配
        if text_a == text_b:
            return 0.95

        # 包含关系
        if text_a in text_b or text_b in text_a:
            shorter = min(len(text_a), len(text_b))
            longer = max(len(text_a), len(text_b))
            if shorter / longer > 0.8:
                return 0.85
            return 0.7

        # 相似度
        sim = self._text_similarity(text_a, text_b)
        if sim > 0.85:
            return 0.8
        if sim > 0.75:
            return 0.65
        return sim * 0.5

    def _build_suggestion(self, pair: tuple[dict, dict], confidence: float) -> dict:
        """构建合并建议"""
        a, b = pair
        # paper_count 大的作为 target
        if a.get("paper_count", 0) >= b.get("paper_count", 0):
            source, target = b, a
        else:
            source, target = a, b

        rationale = self._build_rationale(source, target, confidence)

        return {
            "id": str(uuid.uuid4()),
            "source": {
                "id": source["id"],
                "text": source.get("text", ""),
                "paper_count": source.get("paper_count", 0),
            },
            "target": {
                "id": target["id"],
                "text": target.get("text", ""),
                "paper_count": target.get("paper_count", 0),
            },
            "confidence": round(confidence, 2),
            "rationale": rationale,
        }

    def _build_rationale(self, source: dict, target: dict, confidence: float) -> str:
        """生成合并理由"""
        text_a = source.get("text", "").lower()
        text_b = target.get("text", "").lower()

        if text_a == text_b:
            return "两个概念名称完全相同，建议合并。"
        if text_a in text_b or text_b in text_a:
            return f"概念名称存在包含关系（\"{text_a}\" 与 \"{text_b}\"），可能指向同一概念。"
        return f"概念名称文本相似度较高（{confidence:.0%}），建议人工确认是否合并。"

    def _update(self, scan_id: str, **kwargs):
        """更新扫描状态"""
        updates = []
        values = []
        for key, value in kwargs.items():
            updates.append(f"{key} = ?")
            values.append(value)

        if updates:
            values.append(scan_id)
            self.db.execute_write(
                f"UPDATE dedup_scans SET {', '.join(updates)} WHERE id = ?",
                tuple(values),
            )

    def get_scan_status(self, scan_id: str) -> dict | None:
        """获取扫描状态"""
        cursor = self.db.execute_read(
            "SELECT * FROM dedup_scans WHERE id = ?",
            (scan_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        result = dict(row)
        # 解析 suggestions JSON
        if result.get("suggestions") and isinstance(result["suggestions"], str):
            try:
                result["suggestions"] = json.loads(result["suggestions"])
            except (json.JSONDecodeError, TypeError):
                result["suggestions"] = []
        else:
            result["suggestions"] = []

        return result

    def update_scan_status(self, scan_id: str, **kwargs):
        """更新扫描状态（公开接口）"""
        self._update(scan_id, **kwargs)

    def execute_merge(self, scan_id: str, merge_ids: list[str]) -> dict:
        """执行概念合并"""
        scan = self.get_scan_status(scan_id)
        if not scan:
            return {"executed": 0, "details": [], "error": "Scan not found"}

        suggestions = scan.get("suggestions", [])
        if not suggestions:
            return {"executed": 0, "details": [], "error": "No suggestions available"}

        # 构建 suggestion lookup
        sug_map = {s["id"]: s for s in suggestions}

        executed = 0
        details = []
        floating_fixed = 0
        floating_details = []

        for merge_id in merge_ids:
            sug = sug_map.get(merge_id)
            if not sug:
                details.append({
                    "source": "unknown",
                    "target": "unknown",
                    "status": "failed",
                    "message": "Suggestion not found",
                })
                continue

            source_id = sug["source"]["id"]
            target_id = sug["target"]["id"]

            try:
                # 获取 source 概念的论文关联
                source_papers = self.db.concepts.get_papers(source_id)

                # 将 source 的论文重新关联到 target
                for p in source_papers:
                    paper_doi = p.get("paper_doi")
                    if paper_doi:
                        self.db.execute_write(
                            "INSERT OR IGNORE INTO paper_concepts (paper_doi, concept_id) VALUES (?, ?)",
                            (paper_doi, target_id),
                        )

                # 更新 target 的 paper_count
                new_count = sug["source"]["paper_count"] + sug["target"]["paper_count"]
                self.db.execute_write(
                    "UPDATE concepts SET paper_count = ? WHERE id = ?",
                    (new_count, target_id),
                )

                # 删除关联记录（必须在删除概念之前，因为有 FK 约束）
                self.db.execute_write(
                    "DELETE FROM paper_concepts WHERE concept_id = ?",
                    (source_id,),
                )
                self.db.execute_write(
                    "DELETE FROM concept_relations WHERE parent_id = ?",
                    (source_id,),
                )
                self.db.execute_write(
                    "DELETE FROM concept_relations WHERE child_id = ?",
                    (source_id,),
                )

                # 最后删除概念本身
                self.db.execute_write(
                    "DELETE FROM concepts WHERE id = ?",
                    (source_id,),
                )

                executed += 1
                details.append({
                    "source": sug["source"]["text"],
                    "target": sug["target"]["text"],
                    "status": "success",
                })
            except Exception as e:
                details.append({
                    "source": sug["source"]["text"],
                    "target": sug["target"]["text"],
                    "status": "failed",
                    "message": str(e),
                })

        return {
            "executed": executed,
            "details": details,
            "floating_fixed": floating_fixed,
            "floating_details": floating_details,
        }

    def cleanup_old_scans(self, max_age_hours: int = 24):
        """清理旧的扫描任务"""
        self.db.execute_write("""
            DELETE FROM dedup_scans
            WHERE created_at < datetime('now', ?)
        """, (f'-{max_age_hours} hours',))
