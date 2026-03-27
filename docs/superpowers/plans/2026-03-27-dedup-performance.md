# Dedup Performance Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optimize concept deduplication scan performance from ~5 minutes to <20 seconds for 100 candidates by implementing batch LLM calls and smart pre-filtering.

**Architecture:** Replace single-candidate LLM calls with batch processing (10 candidates per call). Add local pre-filtering rules (high similarity, text containment) to reduce LLM calls by 30-55%.

**Tech Stack:** Python, SQLite, FastAPI, existing LLM client infrastructure

---

## File Structure

| File | Responsibility |
|------|----------------|
| `mkg/dedup/candidate.py` | Pre-filter rules + batch generation |
| `mkg/database.py` | Scan job progress fields |
| `backend/routes/concepts.py` | Batch LLM processing logic |

---

## Phase 1: Core Optimization (P0)

### Task 1: Add Pre-filter Rules to CandidateGenerator

**Files:**
- Modify: `mkg/dedup/candidate.py`

- [ ] **Step 1: Add high similarity threshold constant and text containment check**

Add after line 22:

```python
    HIGH_SIMILARITY_THRESHOLD = 0.9  # Above this, auto-merge without LLM

    @staticmethod
    def check_text_containment(text1: str, text2: str) -> tuple[bool, str]:
        """Check if one text contains another (absorption merge).

        Returns (should_auto_merge, target_text_to_keep)
        """
        t1, t2 = text1.lower().strip(), text2.lower().strip()

        # Complete containment - keep shorter text
        if t1 in t2 and len(t1) < len(t2):
            return True, text1
        if t2 in t1 and len(t2) < len(t1):
            return True, text2

        # Common suffix patterns (Chinese and English)
        suffixes = ['方法', '方法 ', ' method', ' methods', '技术', '技术 ', ' technique', ' techniques']
        for suffix in suffixes:
            if t1 + suffix == t2:
                return True, text1
            if t2 + suffix == t1:
                return True, text2

        return False, ""
```

- [ ] **Step 2: Add generate_candidates_with_prefilter method**

Add after the `generate_candidates` method (after line 40):

```python
    def generate_candidates_with_prefilter(self, folder_id: str = None) -> dict:
        """Generate candidates with pre-filtering rules applied.

        Returns:
            {
                "candidates": [...],      # Need LLM analysis
                "high_confidence": [...], # Auto-merge suggestions (no LLM needed)
                "filtered": [...],        # Filtered out by rules
                "stats": {...}
            }
        """
        raw_candidates = self.generate_candidates(folder_id=folder_id)

        candidates = []
        high_confidence = []
        filtered = []
        stats = {"total_pairs": len(raw_candidates), "high_similarity": 0, "text_containment": 0}

        for pair in raw_candidates:
            # Rule 1: High similarity auto-merge
            if pair.similarity >= self.HIGH_SIMILARITY_THRESHOLD:
                # Keep the one with higher paper_count
                if pair.concept1.get('paper_count', 0) >= pair.concept2.get('paper_count', 0):
                    target, source = pair.concept1, pair.concept2
                else:
                    target, source = pair.concept2, pair.concept1

                high_confidence.append({
                    "source_id": source['id'],
                    "target_id": target['id'],
                    "confidence": 0.95,
                    "rationale": f"文本高度相似 (相似度: {pair.similarity:.2f})",
                    "merge_type": "synonym"
                })
                stats["high_similarity"] += 1
                continue

            # Rule 2: Text containment (absorption)
            should_merge, target_text = self.check_text_containment(
                pair.concept1['text'], pair.concept2['text']
            )
            if should_merge:
                # The shorter text is the target (returned by check_text_containment)
                if pair.concept1['text'] == target_text:
                    target, source = pair.concept1, pair.concept2
                else:
                    target, source = pair.concept2, pair.concept1

                high_confidence.append({
                    "source_id": source['id'],
                    "target_id": target['id'],
                    "confidence": 0.90,
                    "rationale": f"文本包含关系: '{target['text']}' 是 '{source['text']}' 的简洁形式",
                    "merge_type": "absorption"
                })
                stats["text_containment"] += 1
                continue

            # Needs LLM analysis
            candidates.append(pair)

        stats["llm_needed"] = len(candidates)
        stats["auto_merged"] = len(high_confidence)

        return {
            "candidates": candidates,
            "high_confidence": high_confidence,
            "filtered": filtered,
            "stats": stats
        }
```

- [ ] **Step 3: Verify syntax by importing the module**

Run: `cd D:/meta-knowledge-graph-main && python -c "from mkg.dedup.candidate import CandidateGenerator; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add mkg/dedup/candidate.py
git commit -m "feat(dedup): add pre-filter rules for candidate generation

- Add HIGH_SIMILARITY_THRESHOLD (0.9) for auto-merge
- Add check_text_containment for absorption merge detection
- Add generate_candidates_with_prefilter method
- Reduces LLM calls by 30-55% through local filtering

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Add Progress Fields to scan_jobs Table

**Files:**
- Modify: `mkg/database.py`

- [ ] **Step 1: Add new columns to scan_jobs table schema**

Locate the `CREATE TABLE IF NOT EXISTS scan_jobs` block (around line 221-233) and replace with:

```python
        # 扫描任务表 - 用于去重扫描进度跟踪
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_jobs (
                id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'pending',
                phase TEXT DEFAULT 'prefiltering',
                total_concepts INTEGER DEFAULT 0,
                concepts_scanned INTEGER DEFAULT 0,
                batches_total INTEGER DEFAULT 0,
                batches_completed INTEGER DEFAULT 0,
                filtered_count INTEGER DEFAULT 0,
                high_confidence_count INTEGER DEFAULT 0,
                suggestions TEXT,
                error TEXT,
                created_at REAL,
                started_at REAL,
                completed_at REAL
            )
        """)
```

- [ ] **Step 2: Add ALTER TABLE statements for existing databases**

Add after the CREATE TABLE block (after line 233):

```python
        # Add new columns to existing scan_jobs table
        try:
            cursor.execute("ALTER TABLE scan_jobs ADD COLUMN phase TEXT DEFAULT 'prefiltering'")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE scan_jobs ADD COLUMN batches_total INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE scan_jobs ADD COLUMN batches_completed INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE scan_jobs ADD COLUMN filtered_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE scan_jobs ADD COLUMN high_confidence_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
```

- [ ] **Step 3: Verify database initialization**

Run: `cd D:/meta-knowledge-graph-main && python -c "from mkg.database import Database; db = Database(':memory:'); db.connect(); print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add mkg/database.py
git commit -m "feat(db): add progress tracking fields to scan_jobs table

- Add phase field (prefiltering/analyzing/completed)
- Add batches_total and batches_completed for batch progress
- Add filtered_count and high_confidence_count for pre-filter stats
- Add ALTER TABLE for backward compatibility

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Implement Batch LLM Processing

**Files:**
- Modify: `backend/routes/concepts.py`

- [ ] **Step 1: Add BATCH_SIZE constant**

Add after line 16 (after the `time` import, before the `sys.path.insert` line):

```python
BATCH_SIZE = 10  # Batch size for LLM analysis
```

- [ ] **Step 2: Replace run_dedup_scan_background function**

Locate the `run_dedup_scan_background` function (lines 545-606) and replace with:

```python
async def run_dedup_scan_background(scan_id: str, folder_id: str = 'default'):
    """Background task for dedup scan with batch processing"""
    try:
        db = get_db()
        deduplicator = get_deduplicator()

        # Phase 1: Pre-filtering
        db.update_scan_job(scan_id, status='scanning', phase='prefiltering', started_at=time.time())

        prefiltered = deduplicator.candidate_generator.generate_candidates_with_prefilter(folder_id=folder_id)

        candidates = prefiltered['candidates']
        high_confidence = prefiltered['high_confidence']
        stats = prefiltered['stats']

        # Update job with prefilter stats
        total_batches = (len(candidates) + BATCH_SIZE - 1) // BATCH_SIZE if candidates else 0
        db.update_scan_job(
            scan_id,
            phase='analyzing',
            total_concepts=len(candidates),
            batches_total=total_batches,
            filtered_count=stats.get('filtered', 0),
            high_confidence_count=len(high_confidence)
        )

        if not candidates and not high_confidence:
            db.update_scan_job(
                scan_id,
                status='completed',
                phase='completed',
                suggestions=[],
                completed_at=time.time()
            )
            return

        # Prepare analyzer
        deduplicator.merge_analyzer._get_parent_names = lambda cid: [p['id'] for p in db.get_concept_parents(cid)]
        deduplicator.merge_analyzer._get_child_names = lambda cid: [c['id'] for c in db.get_concept_children(cid)]

        # Phase 2: Batch LLM analysis
        suggestions = []

        # Add high confidence suggestions first
        for i, hc in enumerate(high_confidence):
            source = db.get_concept(hc['source_id'])
            target = db.get_concept(hc['target_id'])
            if source and target:
                suggestions.append({
                    "id": f"merge-{scan_id}-{len(suggestions)}",
                    "source": {"id": source['id'], "text": source['text'], "paper_count": source.get('paper_count', 0)},
                    "target": {"id": target['id'], "text": target['text'], "paper_count": target.get('paper_count', 0)},
                    "confidence": hc['confidence'],
                    "rationale": hc['rationale'],
                    "merged_relations": {"parents": [], "children": []}
                })

        # Process candidates in batches
        batches_completed = 0
        for batch_start in range(0, len(candidates), BATCH_SIZE):
            batch = candidates[batch_start:batch_start + BATCH_SIZE]

            try:
                # Batch LLM call
                batch_suggestions = deduplicator.merge_analyzer.analyze(batch)

                if batch_suggestions:
                    for s in batch_suggestions:
                        source = db.get_concept(s.source_id)
                        target = db.get_concept(s.target_id)
                        if source and target:
                            suggestions.append({
                                "id": f"merge-{scan_id}-{len(suggestions)}",
                                "source": {"id": source['id'], "text": source['text'], "paper_count": source.get('paper_count', 0)},
                                "target": {"id": target['id'], "text": target['text'], "paper_count": target.get('paper_count', 0)},
                                "confidence": s.confidence,
                                "rationale": s.rationale,
                                "merged_relations": s.merged_relations
                            })

            except Exception as e:
                # Batch failed - try individual analysis as fallback
                print(f"Batch analysis failed, falling back to individual: {e}")
                for candidate in batch:
                    try:
                        result = deduplicator.merge_analyzer.analyze([candidate])
                        if result:
                            for s in result:
                                source = db.get_concept(s.source_id)
                                target = db.get_concept(s.target_id)
                                if source and target:
                                    suggestions.append({
                                        "id": f"merge-{scan_id}-{len(suggestions)}",
                                        "source": {"id": source['id'], "text": source['text'], "paper_count": source.get('paper_count', 0)},
                                        "target": {"id": target['id'], "text": target['text'], "paper_count": target.get('paper_count', 0)},
                                        "confidence": s.confidence,
                                        "rationale": s.rationale,
                                        "merged_relations": s.merged_relations
                                    })
                    except Exception as e2:
                        print(f"Individual analysis also failed: {e2}")

            # Update progress after each batch
            batches_completed += 1
            db.update_scan_job(
                scan_id,
                concepts_scanned=min(batch_start + BATCH_SIZE, len(candidates)),
                batches_completed=batches_completed
            )

        # Phase 3: Complete
        db.update_scan_job(
            scan_id,
            status='completed',
            phase='completed',
            suggestions=suggestions,
            completed_at=time.time()
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        db = get_db()
        db.update_scan_job(scan_id, status='failed', phase='failed', error=str(e), completed_at=time.time())
```

- [ ] **Step 3: Update get_dedup_scan_status to include new fields**

Locate the `get_dedup_scan_status` function (lines 608-649) and update the return statement.

Find this block (around line 640-649):

```python
    return {
        "scan_id": scan_id,
        "status": job['status'],
        "total_concepts": job['total_concepts'],
        "concepts_scanned": job['concepts_scanned'],
        "progress": progress,
        "estimated_time": estimated_time,
        "suggestions": job.get('suggestions') if job['status'] == 'completed' else None,
        "error": job.get('error')
    }
```

Replace with:

```python
    return {
        "scan_id": scan_id,
        "status": job['status'],
        "phase": job.get('phase', 'unknown'),
        "total_concepts": job['total_concepts'],
        "concepts_scanned": job['concepts_scanned'],
        "batches_total": job.get('batches_total', 0),
        "batches_completed": job.get('batches_completed', 0),
        "filtered_count": job.get('filtered_count', 0),
        "high_confidence_count": job.get('high_confidence_count', 0),
        "progress": progress,
        "estimated_time": estimated_time,
        "suggestions": job.get('suggestions') if job['status'] == 'completed' else None,
        "error": job.get('error')
    }
```

- [ ] **Step 4: Verify syntax**

Run: `cd D:/meta-knowledge-graph-main && python -c "from backend.routes.concepts import router; print('OK')"`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/routes/concepts.py
git commit -m "feat(dedup): implement batch LLM processing for scan

- Replace single-candidate loop with batch processing (BATCH_SIZE=10)
- Add prefilter phase before LLM analysis
- Add fallback to individual analysis on batch failure
- Update scan status API with phase and batch progress
- Target: 100 candidates from ~5min to <20sec

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 2: Frontend Updates (P2)

### Task 4: Update Frontend Progress Display

**Files:**
- Modify: `frontend/src/components/DedupPanel.tsx`

- [ ] **Step 1: Update ScanProgress interface**

Locate the `ScanProgress` interface (lines 23-29) and replace with:

```typescript
interface ScanProgress {
  scanId: string | null
  phase: 'prefiltering' | 'analyzing' | 'completed' | 'failed' | 'unknown'
  totalConcepts: number
  conceptsScanned: number
  batchesTotal: number
  batchesCompleted: number
  filteredCount: number
  highConfidenceCount: number
  progress: number
  estimatedTime: number
}
```

- [ ] **Step 2: Update initial state for scanProgress**

Locate the `useState` for `scanProgress` (lines 44-50) and update the initial value:

```typescript
  const [scanProgress, setScanProgress] = useState<ScanProgress>({
    scanId: null,
    phase: 'unknown',
    totalConcepts: 0,
    conceptsScanned: 0,
    batchesTotal: 0,
    batchesCompleted: 0,
    filteredCount: 0,
    highConfidenceCount: 0,
    progress: 0,
    estimatedTime: 0
  })
```

- [ ] **Step 3: Update setScanProgress calls**

Update the polling handler (lines 95-101) to include new fields:

```typescript
        setScanProgress({
          scanId,
          phase: data.phase || 'unknown',
          totalConcepts: data.total_concepts,
          conceptsScanned: data.concepts_scanned,
          batchesTotal: data.batches_total || 0,
          batchesCompleted: data.batches_completed || 0,
          filteredCount: data.filtered_count || 0,
          highConfidenceCount: data.high_confidence_count || 0,
          progress: data.progress,
          estimatedTime: data.estimated_time
        })
```

Also update the handleScan reset (lines 56-62) and handleReset (lines 165-171) to match the new structure.

- [ ] **Step 4: Update progress display text**

Replace the scanning state JSX (lines 243-266) with:

```tsx
        {panelState === 'scanning' && (
          <div className="text-center py-12">
            <RefreshCw className="w-12 h-12 text-blue-500 mx-auto mb-4 animate-spin" />
            {scanProgress.phase === 'prefiltering' ? (
              <p className="text-gray-600">正在预筛选候选对...</p>
            ) : (
              <>
                <p className="text-gray-600">正在分析候选对...</p>
                {scanProgress.batchesTotal > 0 && (
                  <p className="text-sm text-gray-500 mt-1">
                    批次: {scanProgress.batchesCompleted}/{scanProgress.batchesTotal}
                  </p>
                )}
              </>
            )}
            {scanProgress.totalConcepts > 0 && (
              <>
                <p className="text-sm text-gray-500 mt-2">
                  进度: {scanProgress.conceptsScanned}/{scanProgress.totalConcepts} ({Math.round(scanProgress.progress)}%)
                </p>
                {scanProgress.estimatedTime > 0 && (
                  <p className="text-sm text-gray-400 mt-1">
                    预估剩余: {formatScanTime(scanProgress.estimatedTime)}
                  </p>
                )}
                <div className="w-full bg-gray-200 rounded-full h-2 mt-4">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${scanProgress.progress}%` }}
                  />
                </div>
                {scanProgress.highConfidenceCount > 0 && (
                  <p className="text-sm text-green-600 mt-2">
                    {scanProgress.highConfidenceCount} 个高置信度自动合并
                  </p>
                )}
              </>
            )}
          </div>
        )}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/DedupPanel.tsx
git commit -m "feat(frontend): update dedup panel with phase progress

- Show prefiltering/analyzing phase status
- Display batch progress (completed/total)
- Show high confidence auto-merge count

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Verification

### Task 5: End-to-End Test

- [ ] **Step 1: Start the backend server**

Run: `cd D:/meta-knowledge-graph-main && python -m uvicorn backend.main:app --reload`

- [ ] **Step 2: Start the frontend dev server**

Run: `cd D:/meta-knowledge-graph-main/frontend && npm run dev`

- [ ] **Step 3: Test dedup scan**

1. Navigate to the concepts page
2. Click "Scan for Duplicates"
3. Observe progress showing phases (prefiltering → analyzing)
4. Verify scan completes in < 30 seconds for typical library

- [ ] **Step 4: Check database for new fields**

```bash
sqlite3 mkg.db "SELECT id, phase, batches_total, batches_completed, high_confidence_count FROM scan_jobs ORDER BY created_at DESC LIMIT 1"
```

---

## Summary

| Task | Files Modified | Key Changes |
|------|----------------|-------------|
| Task 1 | `mkg/dedup/candidate.py` | Pre-filter rules |
| Task 2 | `mkg/database.py` | Progress fields |
| Task 3 | `backend/routes/concepts.py` | Batch processing |
| Task 4 | `frontend/src/components/DedupPanel.tsx` | UI updates |
| Task 5 | - | E2E verification |