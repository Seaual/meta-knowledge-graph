"""
概念去重主控制器 - 协调整个去重流程
"""

import threading
from datetime import datetime
import uuid
from typing import Dict, Optional, List

from .candidate import CandidateGenerator
from .analyzer import MergeAnalyzer
from .executor import MergeExecutor
from .floating_fixer import fix_floating_concepts


_scan_results: Dict[str, dict] = {}
_scan_lock = threading.Lock()


def store_scan_result(scan_id: str, result: dict):
    """存储扫描结果"""
    with _scan_lock:
        _scan_results[scan_id] = {"result": result, "created_at": datetime.now()}


def get_scan_result(scan_id: str, db=None) -> Optional[dict]:
    """Get scan result from memory or database"""
    # Check memory first (for backward compatibility with sync scans)
    with _scan_lock:
        entry = _scan_results.get(scan_id)
        if entry:
            if (datetime.now() - entry["created_at"]).total_seconds() > 3600:
                del _scan_results[scan_id]
            else:
                return entry["result"]

    # Check database (for async scans)
    if db:
        job = db.get_scan_job(scan_id)
        if job and job.get('status') == 'completed':
            suggestions = job.get('suggestions') or []
            return {
                "scan_id": scan_id,
                "status": "completed",
                "merge_suggestions": suggestions
            }

    return None


def generate_scan_id() -> str:
    """生成扫描 ID"""
    return f"scan-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"


class ConceptDeduplicator:
    """概念去重主控制器"""

    def __init__(self, db, llm_client=None):
        self.db = db
        self.llm_client = llm_client
        self.candidate_generator = CandidateGenerator(db)
        self.merge_executor = MergeExecutor(db)
        self.merge_analyzer = MergeAnalyzer(llm_client) if llm_client else None

    def scan(self) -> dict:
        """执行去重扫描"""
        scan_id = generate_scan_id()
        candidates = self.candidate_generator.generate_candidates()

        if not candidates:
            result = {"scan_id": scan_id, "status": "completed", "candidates_found": 0, "merge_suggestions": []}
            store_scan_result(scan_id, result)
            return result

        if not self.merge_analyzer:
            result = {"scan_id": scan_id, "status": "error", "error": "LLM not configured",
                      "candidates_found": len(candidates), "merge_suggestions": []}
            store_scan_result(scan_id, result)
            return result

        suggestions = self.merge_analyzer.analyze(candidates)

        merge_suggestions = []
        for i, s in enumerate(suggestions):
            source = self.db.get_concept(s.source_id)
            target = self.db.get_concept(s.target_id)
            if not source or not target:
                continue
            merge_suggestions.append({
                "id": f"merge-{scan_id}-{i}",
                "source": {"id": source['id'], "text": source['text'], "paper_count": source.get('paper_count', 0)},
                "target": {"id": target['id'], "text": target['text'], "paper_count": target.get('paper_count', 0)},
                "confidence": s.confidence,
                "rationale": s.rationale,
                "merge_type": s.merge_type
            })

        result = {"scan_id": scan_id, "status": "completed", "candidates_found": len(candidates),
                  "merge_suggestions": merge_suggestions}
        store_scan_result(scan_id, result)
        return result

    def execute_merge(self, scan_id: str, merge_ids: List[str]) -> dict:
        """执行合并操作"""
        # Pass db to get_scan_result to check database
        scan_result = get_scan_result(scan_id, self.db)
        if not scan_result:
            return {"executed": 0, "error": "Scan result not found or expired"}

        suggestions_map = {s['id']: s for s in scan_result.get('merge_suggestions', [])}

        details = []
        executed = 0

        for merge_id in merge_ids:
            suggestion = suggestions_map.get(merge_id)
            if not suggestion:
                details.append({"merge_id": merge_id, "status": "failed", "message": "Merge suggestion not found"})
                continue

            result = self.merge_executor.execute(
                source_id=suggestion['source']['id'],
                target_id=suggestion['target']['id']
            )

            details.append({
                "source": suggestion['source']['id'],
                "target": suggestion['target']['id'],
                "status": result.status,
                "message": result.message
            })

            if result.status == 'success':
                executed += 1

        # 自动修复漂浮概念
        floating_result = {'fixed': 0, 'details': []}
        if executed > 0:
            floating_result = fix_floating_concepts(self.db, self.llm_client)

        return {
            "executed": executed,
            "details": details,
            "floating_fixed": floating_result['fixed'],
            "floating_details": floating_result.get('details', [])
        }