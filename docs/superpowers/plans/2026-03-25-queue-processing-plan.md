# Queue Processing with Time Estimation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement queue-based batch processing with time estimation for PDF uploads, batch paper processing, and deduplication scanning.

**Architecture:** Frontend manages processing queue with sequential task execution, backend provides single-task APIs that return duration for time estimation. Deduplication scanning uses async background tasks with database-backed progress tracking.

**Tech Stack:** React (TypeScript), FastAPI (Python), SQLite

---

## File Structure

| File | Purpose |
|------|---------|
| `frontend/src/pages/Papers.tsx` | PDF upload notification auto-dismiss, batch queue processing with time estimation |
| `frontend/src/components/DedupPanel.tsx` | Dedup scan progress with polling and time estimation |
| `frontend/src/lib/api.ts` | New API methods: `processSingle`, `scanStatus` |
| `backend/routes/papers.py` | New `/process-single` endpoint with duration tracking |
| `backend/routes/concepts.py` | Async scan with `/scan-status` endpoint |
| `mkg/database.py` | `scan_jobs` table and methods |
| `mkg/dedup/deduplicator.py` | Update to read scan results from database |

---

## Task 1: PDF Upload Notification Auto-Dismiss

**Files:**
- Modify: `frontend/src/pages/Papers.tsx`

**Goal:** Make upload results notification disappear after 5 seconds automatically.

### Step 1.1: Add useRef for timer management

Find line ~1 where imports are, add `useRef`:

```typescript
import { useEffect, useState, useRef } from 'react'
```

### Step 1.2: Add timer ref after state declarations

Find around line ~55 where state variables are declared, add after `sidebarCollapsed`:

```typescript
const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
const uploadTimerRef = useRef<NodeJS.Timeout | null>(null)
```

### Step 1.3: Add auto-dismiss useEffect

Add after the `useEffect` that loads papers (around line ~93):

```typescript
// Auto-dismiss upload results after 5 seconds
useEffect(() => {
  if (uploadResults.length === 0) return

  // Clear old timer
  if (uploadTimerRef.current) {
    clearTimeout(uploadTimerRef.current)
  }

  // Set new timer
  uploadTimerRef.current = setTimeout(() => {
    setUploadResults([])
    uploadTimerRef.current = null
  }, 5000)

  return () => {
    if (uploadTimerRef.current) {
      clearTimeout(uploadTimerRef.current)
    }
  }
}, [uploadResults])
```

### Step 1.4: Commit

```bash
git add frontend/src/pages/Papers.tsx
git commit -m "feat: auto-dismiss upload results after 5 seconds

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Backend - Single Paper Process API with Duration

**Files:**
- Modify: `backend/routes/papers.py`

**Goal:** Create `/process-single` endpoint that returns processing duration for time estimation.

### Step 2.1: Add process-single endpoint

Find the `@router.post("/process", ...)` endpoint around line 403. Add new endpoint after it:

```python
@router.post("/process-single")
async def process_single_paper(request: ProcessRequest):
    """
    Process a single paper and return duration for time estimation.

    Same logic as /process but adds duration and concepts_count to response.
    """
    import time
    start_time = time.time()

    db = get_db()
    paper = db.get_paper(request.doi)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    pdf_path = paper.get('pdf_path')
    if not pdf_path or not Path(pdf_path).exists():
        raise HTTPException(status_code=400, detail="PDF file not found")

    extractor = get_extractor()
    if not extractor:
        raise HTTPException(status_code=400, detail="LLM not configured. Claude CLI or API Key required.")

    graph = get_graph()
    existing_concepts = graph.get_concept_tree_summary()

    parser = get_parser()
    content = parser.parse(pdf_path)

    if not content:
        raise HTTPException(status_code=400, detail="Failed to parse PDF")

    try:
        extracted = extractor.extract(content, existing_concepts)
        concept_tree = extracted.concept_tree.to_dict() if extracted.concept_tree else None

        if concept_tree:
            graph.build_from_paper(request.doi, concept_tree)
            db.save_concept_extraction(request.doi, concept_tree, extracted.raw_response)

            duration = time.time() - start_time
            concepts_count = count_concepts(concept_tree)

            return {
                "success": True,
                "message": "Paper processed successfully",
                "concept_tree": concept_tree,
                "duration": duration,
                "concepts_count": concepts_count
            }
        else:
            duration = time.time() - start_time
            return {
                "success": False,
                "message": "Failed to extract concepts",
                "duration": duration,
                "concepts_count": 0
            }

    except Exception as e:
        duration = time.time() - start_time
        raise HTTPException(status_code=500, detail={"error": str(e), "duration": duration})


def count_concepts(tree: dict) -> int:
    """Count total concepts in tree including root"""
    if not tree:
        return 0
    count = 1  # root
    for child in tree.get('children', []):
        count += count_concepts(child)
    return count
```

### Step 2.2: Commit

```bash
git add backend/routes/papers.py
git commit -m "feat: add /process-single endpoint with duration tracking

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Frontend API - Add processSingle Method

**Files:**
- Modify: `frontend/src/lib/api.ts`

**Goal:** Add API method for single paper processing.

### Step 3.1: Add ProcessSingleResponse interface

Find around line ~28 where interfaces are defined, add after `UploadResult`:

```typescript
interface ProcessSingleResponse {
  success: boolean
  message: string
  concept_tree: any | null
  duration: number
  concepts_count: number
}
```

### Step 3.2: Add processSingle method to papersApi

Find the `papersApi` object around line ~11, add after `contribution` method:

```typescript
  processSingle: (doi: string) => api.post<ProcessSingleResponse>('/papers/process-single', { doi }),
```

### Step 3.3: Export the new interface

Find around line ~226 where exports are, add:

```typescript
export type { ProcessSingleResponse }
```

### Step 3.4: Commit

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: add processSingle API method with duration response

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Frontend - Batch Processing Queue with Time Estimation

**Files:**
- Modify: `frontend/src/pages/Papers.tsx`

**Goal:** Replace batch processing with queue-based sequential processing and time estimation.

### Step 4.1: Add QueueState interface

Find around line ~30 where interfaces are defined, add after `Contribution`:

```typescript
interface QueueState {
  pending: string[]
  current: string | null
  completed: number
  successful: number
  failed: number
  estimatedTime: number
  avgTimePerPaper: number
  durations: number[]
}
```

### Step 4.2: Add queue state and MAX_DURATIONS constant

Find around line ~48 where `batchProgress` state is, add after it:

```typescript
const MAX_DURATIONS = 50
const [queueState, setQueueState] = useState<QueueState>({
  pending: [],
  current: null,
  completed: 0,
  successful: 0,
  failed: 0,
  estimatedTime: 0,
  avgTimePerPaper: 0,
  durations: []
})
```

### Step 4.3: Import processSingle from api

Find line ~3 where imports from api are, update to include `ProcessSingleResponse`:

```typescript
import { papersApi, batchApi, foldersApi, ProcessSingleResponse } from '../lib/api'
```

### Step 4.4: Replace handleBatchProcess function

Find `handleBatchProcess` around line ~133. Replace the entire function with:

```typescript
const handleBatchProcess = async () => {
  const pendingPapers = papers.filter(p => p.status === 'pending')
  if (pendingPapers.length === 0) {
    alert('没有待处理的论文')
    return
  }

  // Check if already processing
  if (queueState.current !== null) {
    alert('已有批量处理任务进行中，请等待完成')
    return
  }

  if (!confirm(`确定要处理 ${pendingPapers.length} 篇论文？\n这将按顺序逐个处理，显示实时进度。`)) {
    return
  }

  // Initialize queue
  const dois = pendingPapers.map(p => p.doi)
  setQueueState({
    pending: dois,
    current: dois[0],
    completed: 0,
    successful: 0,
    failed: 0,
    estimatedTime: 0,
    avgTimePerPaper: 0,
    durations: []
  })

  // Process sequentially
  const newDurations: number[] = []
  let successful = 0
  let failed = 0

  for (let i = 0; i < dois.length; i++) {
    const doi = dois[i]

    setQueueState(prev => ({
      ...prev,
      current: doi,
      pending: dois.slice(i + 1),
      completed: i,
      avgTimePerPaper: newDurations.length > 0
        ? newDurations.reduce((a, b) => a + b, 0) / newDurations.length
        : 0
    }))

    try {
      const res = await papersApi.processSingle(doi)
      const duration = res.data.duration

      // Limit durations array
      if (newDurations.length >= MAX_DURATIONS) {
        newDurations.shift()
      }
      newDurations.push(duration)

      if (res.data.success) {
        successful++
      } else {
        failed++
      }
    } catch (err) {
      failed++
      console.error(`Failed to process ${doi}:`, err)
    }

    // Update progress
    const avgTime = newDurations.length > 0
      ? newDurations.reduce((a, b) => a + b, 0) / newDurations.length
      : 0
    const remaining = dois.length - i - 1

    setQueueState(prev => ({
      ...prev,
      completed: i + 1,
      successful,
      failed,
      durations: [...newDurations],
      avgTimePerPaper: avgTime,
      estimatedTime: Math.ceil(avgTime * remaining)
    }))
  }

  // Finish
  setQueueState(prev => ({
    ...prev,
    current: null
  }))

  loadPapers()
  loadFolders()
}
```

### Step 4.5: Update Batch Progress UI to show estimated time

Find the "Batch Progress" section around line ~394. Replace with:

```typescript
          {/* Queue Progress */}
          {(queueState.current !== null || queueState.completed > 0) && (
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-medium mb-3">
                {queueState.current !== null ? '批量处理中...' : '批量处理完成'}
              </h3>
              <div className="flex items-center gap-4">
                <div className="flex-1 bg-gray-200 rounded-full h-2.5">
                  <div
                    className="bg-green-500 h-2.5 rounded-full transition-all"
                    style={{ width: `${(queueState.completed / (queueState.completed + queueState.pending.length)) * 100}%` }}
                  />
                </div>
                <span className="text-sm text-gray-600">
                  {queueState.completed}/{queueState.completed + queueState.pending.length}
                </span>
              </div>
              <div className="flex gap-4 mt-2 text-sm">
                <span className="text-green-600">成功: {queueState.successful}</span>
                <span className="text-red-600">失败: {queueState.failed}</span>
                {queueState.estimatedTime > 0 && queueState.current !== null && (
                  <span className="text-gray-500">
                    预估剩余: {formatTime(queueState.estimatedTime)}
                  </span>
                )}
              </div>
            </div>
          )}
```

### Step 4.6: Add formatTime helper function

Add before the `return` statement (around line ~225):

```typescript
const formatTime = (seconds: number): string => {
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (minutes < 60) return `${minutes}分${secs > 0 ? secs + '秒' : ''}`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours}小时${mins > 0 ? mins + '分' : ''}`
}
```

### Step 4.7: Remove old batchProgress state and related code

Remove:
- The `batchProgress` state declaration (line ~43)
- The `batchProcessing` state declaration (line ~42)
- The old batch progress display section (lines ~394-414)

Update the batch button to use `queueState.current` instead of `batchProcessing`:

```typescript
              {papers.filter(p => p.status === 'pending').length > 0 && (
                <button
                  onClick={handleBatchProcess}
                  disabled={queueState.current !== null}
                  className="flex items-center px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
                >
                  {queueState.current !== null ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      处理中...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-2" />
                      批量处理 ({papers.filter(p => p.status === 'pending').length})
                    </>
                  )}
                </button>
              )}
```

### Step 4.8: Commit

```bash
git add frontend/src/pages/Papers.tsx
git commit -m "feat: implement queue-based batch processing with time estimation

- Replace parallel batch with sequential queue processing
- Show estimated remaining time based on average duration
- Prevent concurrent batch operations
- Update progress UI with real-time stats

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Database - Add scan_jobs Table

**Files:**
- Modify: `mkg/database.py`

**Goal:** Add scan_jobs table for async deduplication scan progress tracking.

### Step 5.1: Add scan_jobs table creation in _init_tables

Find the `_init_tables` method, add after the folders table creation (around line ~175):

```python
        # 扫描任务表 - 用于去重扫描进度跟踪
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_jobs (
                id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'pending',
                total_concepts INTEGER DEFAULT 0,
                concepts_scanned INTEGER DEFAULT 0,
                suggestions TEXT,
                error TEXT,
                created_at REAL,
                started_at REAL,
                completed_at REAL
            )
        """)
```

### Step 5.2: Add scan job methods after batch job methods

Find around line ~835 where batch job methods end, add:

```python
    # ========== 扫描任务操作方法 ==========

    def create_scan_job(self, scan_id: str, total_concepts: int):
        """创建扫描任务"""
        import time
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO scan_jobs (id, total_concepts, status, created_at)
            VALUES (?, ?, 'pending', ?)
        """, (scan_id, total_concepts, time.time()))
        self.conn.commit()

    def get_scan_job(self, scan_id: str) -> Optional[dict]:
        """获取扫描任务状态"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM scan_jobs WHERE id = ?", (scan_id,))
        row = cursor.fetchone()
        if not row:
            return None
        result = dict(row)
        # Parse suggestions JSON if present
        if result.get('suggestions') and isinstance(result['suggestions'], str):
            try:
                import json
                result['suggestions'] = json.loads(result['suggestions'])
            except:
                result['suggestions'] = None
        return result

    def update_scan_job(self, scan_id: str, **kwargs):
        """更新扫描任务状态"""
        import time
        cursor = self.conn.cursor()

        # Build dynamic update query
        set_parts = []
        values = []
        for key, value in kwargs.items():
            if key == 'suggestions' and isinstance(value, (list, dict)):
                import json
                value = json.dumps(value)
            set_parts.append(f"{key} = ?")
            values.append(value)

        if not set_parts:
            return

        values.append(scan_id)
        cursor.execute(f"""
            UPDATE scan_jobs SET {', '.join(set_parts)}
            WHERE id = ?
        """, values)
        self.conn.commit()

    def cleanup_old_scan_jobs(self, max_age_hours: int = 24):
        """清理过期的扫描任务"""
        import time
        cursor = self.conn.cursor()
        cutoff = time.time() - (max_age_hours * 3600)
        cursor.execute(
            "DELETE FROM scan_jobs WHERE completed_at < ? OR (status IN ('completed', 'failed') AND created_at < ?)",
            (cutoff, cutoff)
        )
        self.conn.commit()

    def get_concept_count(self) -> int:
        """获取概念总数"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM concepts")
        return cursor.fetchone()['count']
```

### Step 5.3: Commit

```bash
git add mkg/database.py
git commit -m "feat: add scan_jobs table and methods for async dedup tracking

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Backend - Async Dedup Scan with Progress

**Files:**
- Modify: `backend/routes/concepts.py`

**Goal:** Make dedup scan async with progress tracking.

### Step 6.1: Add imports at the top

Find line ~5-12 where imports are, ensure these are present:

```python
import asyncio
import uuid
import time
```

### Step 6.2: Replace dedup_scan endpoint

Find `@router.post("/dedup/scan")` around line ~503. Replace with:

```python
@router.post("/dedup/scan")
async def start_dedup_scan():
    """
    Start async deduplication scan

    Returns scan_id for polling progress
    """
    db = get_db()
    deduplicator = get_deduplicator()

    if not deduplicator.merge_analyzer:
        raise HTTPException(
            status_code=500,
            detail="LLM not configured. Please set ANTHROPIC_API_KEY, GOOGLE_API_KEY, or DASHSCOPE_API_KEY"
        )

    # Clean up old jobs
    db.cleanup_old_scan_jobs()

    # Create scan job
    scan_id = f"scan-{uuid.uuid4().hex[:8]}"
    total_concepts = db.get_concept_count()
    db.create_scan_job(scan_id, total_concepts)

    # Start background task
    asyncio.create_task(run_dedup_scan_background(scan_id))

    return {
        "scan_id": scan_id,
        "total_concepts": total_concepts,
        "status": "scanning"
    }


async def run_dedup_scan_background(scan_id: str):
    """Background task for dedup scan"""
    try:
        db = get_db()
        deduplicator = get_deduplicator()

        db.update_scan_job(scan_id, status='scanning', started_at=time.time())

        # Get candidates
        candidates = deduplicator.candidate_generator.generate_candidates()

        if not candidates:
            db.update_scan_job(
                scan_id,
                status='completed',
                suggestions=[],
                completed_at=time.time()
            )
            return

        # Prepare analyzer
        deduplicator.merge_analyzer._get_parent_names = lambda cid: [p['id'] for p in db.get_concept_parents(cid)]
        deduplicator.merge_analyzer._get_child_names = lambda cid: [c['id'] for c in db.get_concept_children(cid)]

        # Process candidates one by one for progress tracking
        suggestions = []
        for i, candidate in enumerate(candidates):
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
                                "rationale": s.rationale
                            })
            except Exception as e:
                print(f"Error analyzing candidate {i}: {e}")

            # Update progress
            db.update_scan_job(scan_id, concepts_scanned=i + 1)

        # Complete
        db.update_scan_job(
            scan_id,
            status='completed',
            suggestions=suggestions,
            completed_at=time.time()
        )

    except Exception as e:
        db = get_db()
        db.update_scan_job(scan_id, status='failed', error=str(e), completed_at=time.time())
```

### Step 6.3: Add scan-status endpoint

Add after the `start_dedup_scan` function:

```python
@router.get("/dedup/scan-status/{scan_id}")
def get_dedup_scan_status(scan_id: str):
    """
    Get dedup scan progress

    Returns progress and estimated time remaining
    """
    db = get_db()
    job = db.get_scan_job(scan_id)

    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")

    # Calculate estimated time
    estimated_time = 0
    if job['concepts_scanned'] > 0 and job['total_concepts'] > 0 and job.get('started_at'):
        elapsed = time.time() - job['started_at']
        avg_time = elapsed / job['concepts_scanned']
        remaining = job['total_concepts'] - job['concepts_scanned']
        estimated_time = int(avg_time * remaining)

    # Calculate progress
    progress = 0
    if job['total_concepts'] > 0:
        progress = (job['concepts_scanned'] / job['total_concepts']) * 100

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

### Step 6.4: Commit

```bash
git add backend/routes/concepts.py
git commit -m "feat: make dedup scan async with progress tracking

- Start scan returns scan_id immediately
- Background task processes candidates
- Poll /scan-status for progress and ETA
- Database stores scan job state

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

### Step 6.5: Update deduplicator to read from database

**Files:**
- Modify: `mkg/dedup/deduplicator.py`

The existing `execute_merge` reads scan results from in-memory storage, but the new async scan stores in database. Update to check database first:

Find `get_scan_result` function around line ~25, replace with:

```python
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
            return {
                "scan_id": scan_id,
                "status": "completed",
                "merge_suggestions": job.get('suggestions', [])
            }

    return None
```

Find `execute_merge` method around line ~94, update the call to `get_scan_result`:

```python
def execute_merge(self, scan_id: str, merge_ids: List[str]) -> dict:
    """Execute merge operations"""
    # Pass db to get_scan_result to check database
    scan_result = get_scan_result(scan_id, self.db)
    if not scan_result:
        return {"executed": 0, "error": "Scan result not found or expired"}
    # ... rest remains unchanged
```

### Step 6.6: Commit

```bash
git add mkg/dedup/deduplicator.py
git commit -m "fix: update execute_merge to read scan results from database

- Check database for async scan results
- Maintain backward compatibility with in-memory results

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 8: Frontend API - Add scanStatus Method

**Files:**
- Modify: `frontend/src/lib/api.ts`

**Goal:** Add API method for polling scan status.

### Step 8.1: Add ScanStatusResponse interface

Find around line ~55 where dedup interfaces are, add after `DedupExecuteResponse`:

```typescript
interface ScanStatusResponse {
  scan_id: string
  status: string
  total_concepts: number
  concepts_scanned: number
  progress: number
  estimated_time: number
  suggestions: MergeSuggestion[] | null
  error?: string
}
```

### Step 8.2: Update scan method return type and add scanStatus

Find the `dedupApi` object around line ~75, update to:

```typescript
// Dedup API
export const dedupApi = {
  scan: () => api.post<{ scan_id: string; total_concepts: number; status: string }>('/concepts/dedup/scan'),
  scanStatus: (scanId: string) => api.get<ScanStatusResponse>(`/concepts/dedup/scan-status/${scanId}`),
  execute: (scanId: string, mergeIds: string[]) =>
    api.post<DedupExecuteResponse>('/concepts/dedup/execute', {
      scan_id: scanId,
      merge_ids: mergeIds,
    }),
}
```

### Step 8.3: Export the new interface

```typescript
export type { ScanStatusResponse }
```

### Step 8.4: Commit

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: add scanStatus API method for polling dedup progress

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 9: Frontend - Dedup Panel with Progress and Time Estimation

**Files:**
- Modify: `frontend/src/components/DedupPanel.tsx`

**Goal:** Update DedupPanel to poll scan status and show progress with estimated time.

### Step 9.1: Add useRef import

Update imports at line ~1:

```typescript
import { useState, useEffect, useRef } from 'react'
```

### Step 9.2: Import ScanStatusResponse

Update api import:

```typescript
import { dedupApi, ScanStatusResponse } from '../lib/api'
```

### Step 9.3: Add ScanProgress state interface and state

Find around line ~30, add after `PanelState` type:

```typescript
interface ScanProgress {
  scanId: string | null
  totalConcepts: number
  conceptsScanned: number
  progress: number
  estimatedTime: number
}
```

Then add state after the existing state declarations:

```typescript
const [scanProgress, setScanProgress] = useState<ScanProgress>({
  scanId: null,
  totalConcepts: 0,
  conceptsScanned: 0,
  progress: 0,
  estimatedTime: 0
})
const pollingRef = useRef<NodeJS.Timeout | null>(null)
```

### Step 9.4: Replace handleScan function

Find `handleScan` around line ~36, replace with:

```typescript
const handleScan = async () => {
  setPanelState('scanning')
  setError(null)
  setScanProgress({
    scanId: null,
    totalConcepts: 0,
    conceptsScanned: 0,
    progress: 0,
    estimatedTime: 0
  })

  try {
    // Start scan
    const res = await dedupApi.scan()
    const scanId = res.data.scan_id

    setScanProgress(prev => ({
      ...prev,
      scanId,
      totalConcepts: res.data.total_concepts
    }))

    // Start polling
    startPolling(scanId)
  } catch (err: any) {
    setError(err.response?.data?.detail || '扫描启动失败')
    setPanelState('idle')
  }
}

const startPolling = (scanId: string) => {
  // Clear existing polling
  if (pollingRef.current) {
    clearInterval(pollingRef.current)
  }

  pollingRef.current = setInterval(async () => {
    try {
      const res = await dedupApi.scanStatus(scanId)
      const data = res.data

      setScanProgress({
        scanId,
        totalConcepts: data.total_concepts,
        conceptsScanned: data.concepts_scanned,
        progress: data.progress,
        estimatedTime: data.estimated_time
      })

      if (data.status === 'completed') {
        // Stop polling
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }

        if (data.suggestions) {
          setSuggestions(data.suggestions)
          setSelectedIds(new Set(data.suggestions.map(s => s.id)))
        } else {
          setSuggestions([])
        }
        setPanelState('review')
      } else if (data.status === 'failed') {
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }
        setError(data.error || '扫描失败')
        setPanelState('idle')
      }
    } catch (err: any) {
      console.error('Poll error:', err)
    }
  }, 1000) // Poll every second
}
```

### Step 9.5: Add cleanup useEffect

Add after the existing useEffects:

```typescript
// Cleanup polling on unmount
useEffect(() => {
  return () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
    }
  }
}, [])
```

### Step 9.6: Update Scanning State UI

Find the "Scanning State" section around line ~130, replace with:

```typescript
        {/* Scanning State */}
        {panelState === 'scanning' && (
          <div className="text-center py-12">
            <RefreshCw className="w-12 h-12 text-blue-500 mx-auto mb-4 animate-spin" />
            <p className="text-gray-600">正在扫描概念...</p>
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
              </>
            )}
          </div>
        )}
```

### Step 9.7: Add formatScanTime helper

Add before the `return` statement:

```typescript
const formatScanTime = (seconds: number): string => {
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (minutes < 60) return `${minutes}分${secs > 0 ? secs + '秒' : ''}`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours}小时${mins > 0 ? mins + '分' : ''}`
}
```

### Step 9.8: Update handleReset

Update `handleReset` to also clear scan progress:

```typescript
const handleReset = () => {
  setPanelState('idle')
  setScanId('')
  setSuggestions([])
  setSelectedIds(new Set())
  setExecuteDetails([])
  setError(null)
  setScanProgress({
    scanId: null,
    totalConcepts: 0,
    conceptsScanned: 0,
    progress: 0,
    estimatedTime: 0
  })
  if (pollingRef.current) {
    clearInterval(pollingRef.current)
    pollingRef.current = null
  }
}
```

### Step 9.9: Commit

```bash
git add frontend/src/components/DedupPanel.tsx
git commit -m "feat: add dedup scan progress with time estimation

- Poll scan status every second
- Show progress bar and percentage
- Display estimated remaining time
- Cleanup polling on unmount

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 10: Final Testing and Integration

**Goal:** Verify all features work together.

### Step 10.1: Test PDF upload auto-dismiss

1. Upload a PDF file
2. Verify the upload result notification appears
3. Wait 5 seconds
4. Verify it disappears automatically
5. Upload multiple files quickly
6. Verify timer resets and all results show until 5 seconds after last upload

### Step 10.2: Test batch processing queue

1. Upload multiple PDFs (3-5)
2. Click "批量处理"
3. Verify:
   - Progress shows current/total
   - Estimated time updates after each paper
   - Papers processed sequentially
   - Cannot start another batch while running
   - Success/failure counts accurate

### Step 10.3: Test dedup scan progress

1. Open dedup panel
2. Click "开始扫描"
3. Verify:
   - Progress bar shows
   - Progress percentage updates
   - Estimated time shows
   - Polling stops when complete
   - Merge suggestions display

### Step 10.4: Final commit

```bash
git add -A
git commit -m "chore: verify all queue processing features work

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | PDF upload auto-dismiss | `Papers.tsx` |
| 2 | Backend process-single API | `papers.py` |
| 3 | Frontend processSingle method | `api.ts` |
| 4 | Batch queue with time estimation | `Papers.tsx` |
| 5 | Database scan_jobs table | `database.py` |
| 6 | Async dedup scan backend | `concepts.py` |
| 6.5 | Update deduplicator for database | `deduplicator.py` |
| 8 | Frontend scanStatus method | `api.ts` |
| 9 | Dedup panel with progress | `DedupPanel.tsx` |
| 10 | Testing and integration | All files |