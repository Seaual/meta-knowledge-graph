---
name: Queue-based Processing with Time Estimation
description: Implement queue-based batch processing with time estimation for PDF uploads, batch processing, and deduplication scanning
type: project
---

# 队列化处理与时间预估设计

## 背景

当前项目存在以下问题：
1. PDF 上传后提示不会自动消失
2. 批量处理没有真正的队列机制，前端等待整个请求完成，无法显示实时进度
3. 去重扫描缺少进度和预估时间

## 目标

1. 上传提示在 5 秒后自动消失
2. 批量处理采用队列形式，逐个处理并显示预估剩余时间
3. 去重扫描显示进度和预估时间

## 设计决策

- **上传提示消失方式**：自动超时消失（5秒）
- **队列实现位置**：混合方案（前端管理队列，后端提供单任务 API）
- **时间预估方式**：基于历史数据（根据已处理任务的平均时间估算）

---

## 1. PDF 上传提示自动消失

### 1.1 改动文件

`frontend/src/pages/Papers.tsx`

### 1.2 实现方式

添加 `useEffect` 监听 `uploadResults` 变化，启动 5 秒定时器后自动清空。

```typescript
useEffect(() => {
  if (uploadResults.length === 0) return

  const timer = setTimeout(() => {
    setUploadResults([])
  }, 5000)

  return () => clearTimeout(timer)
}, [uploadResults])
```

### 1.3 用户交互

```
用户上传文件 → 显示上传结果 → 5秒后自动淡出消失
```

---

## 2. 批量处理队列化

### 2.1 前端改动

**文件**：`frontend/src/pages/Papers.tsx`

#### 2.1.1 新增状态

```typescript
interface QueueState {
  pending: string[]        // 待处理 DOI 队列
  current: string | null   // 当前处理的 DOI
  completed: number
  successful: number
  failed: number
  estimatedTime: number    // 预估剩余秒数
  avgTimePerPaper: number  // 平均每篇处理时间
  durations: number[]      // 每篇实际耗时记录
}
```

#### 2.1.2 处理流程

```
点击批量处理 → 将 pending 论文入队 → 逐个调用 processOne API
→ 每完成一个更新进度 → 计算预估时间 → 完成后显示总结
```

#### 2.1.3 预估时间计算

```typescript
// 基于历史数据计算
avgTimePerPaper = durations.reduce((a, b) => a + b, 0) / durations.length
estimatedTime = Math.ceil(avgTimePerPaper * pending.length)
```

#### 2.1.4 UI 显示

```
批量处理中...
进度: 3/10
成功: 2  失败: 1
预估剩余时间: 约 2 分 30 秒
```

### 2.2 后端改动

**文件**：`backend/routes/papers.py`

#### 2.2.1 新增 API

```python
@router.post("/process-one/{doi}")
async def process_one_paper(doi: str):
    """
    处理单个论文，返回处理耗时

    Returns:
        {
            "success": bool,
            "doi": str,
            "duration": float,  # 处理耗时（秒）
            "concepts": int,    # 提取的概念数
            "error": str | None
        }
    """
    start_time = time.time()
    # ... 现有的处理逻辑
    duration = time.time() - start_time
    return {
        "success": True,
        "doi": doi,
        "duration": duration,
        "concepts": concept_count
    }
```

### 2.3 API 层改动

**文件**：`frontend/src/lib/api.ts`

```typescript
// 新增
papersApi: {
  // ... 现有方法
  processOne: (doi: string) => api.post(`/papers/process-one/${encodeURIComponent(doi)}`)
}
```

---

## 3. 去重扫描预估时间

### 3.1 前端改动

**文件**：`frontend/src/components/DedupPanel.tsx`

#### 3.1.1 新增状态

```typescript
interface ScanProgress {
  scanId: string | null
  status: 'idle' | 'scanning' | 'review' | 'executing' | 'result'
  progress: number         // 0-100
  estimatedTime: number    // 预估剩余秒数
  conceptsScanned: number  // 已扫描概念数
  totalConcepts: number    // 总概念数
  avgTimePerConcept: number // 平均每个概念扫描时间
}
```

#### 3.1.2 处理流程

```
点击开始扫描 → 调用 scan API 获取 scan_id → 轮询 scan-status
→ 显示进度和预估时间 → 完成后显示合并建议
```

#### 3.1.3 UI 显示

```
正在扫描概念...
进度: 45/120 (37%)
预估剩余时间: 约 1 分 20 秒
```

### 3.2 后端改动

**文件**：`backend/routes/concepts.py`

#### 3.2.1 改造扫描为异步

```python
# 数据库存储扫描任务状态
# scan_jobs 表:
# - id: str
# - status: str (pending/scanning/completed/failed)
# - total_concepts: int
# - concepts_scanned: int
# - suggestions: json (完成后存储)
# - created_at: datetime
# - started_at: datetime
# - completed_at: datetime

@router.post("/dedup/scan")
async def start_dedup_scan():
    """
    启动去重扫描（异步）

    Returns:
        {
            "scan_id": str,
            "total_concepts": int,
            "status": "scanning"
        }
    """
    scan_id = str(uuid.uuid4())
    total_concepts = db.get_concept_count()

    # 存储初始状态
    db.create_scan_job(scan_id, total_concepts)

    # 启动后台任务
    asyncio.create_task(run_dedup_scan_background(scan_id))

    return {
        "scan_id": scan_id,
        "total_concepts": total_concepts,
        "status": "scanning"
    }


@router.get("/dedup/scan-status/{scan_id}")
def get_scan_status(scan_id: str):
    """
    获取扫描进度

    Returns:
        {
            "scan_id": str,
            "status": str,
            "total_concepts": int,
            "concepts_scanned": int,
            "progress": float (0-100),
            "estimated_time": int (秒),
            "suggestions": list | null (完成后)
        }
    """
    job = db.get_scan_job(scan_id)
    if not job:
        raise HTTPException(404, "Scan job not found")

    # 计算预估时间
    if job['concepts_scanned'] > 0:
        elapsed = time.time() - job['started_at']
        avg_time = elapsed / job['concepts_scanned']
        remaining = job['total_concepts'] - job['concepts_scanned']
        estimated_time = int(avg_time * remaining)
    else:
        estimated_time = 0

    return {
        "scan_id": scan_id,
        "status": job['status'],
        "total_concepts": job['total_concepts'],
        "concepts_scanned": job['concepts_scanned'],
        "progress": (job['concepts_scanned'] / job['total_concepts']) * 100,
        "estimated_time": estimated_time,
        "suggestions": job.get('suggestions')
    }
```

#### 3.2.2 后台扫描任务

```python
async def run_dedup_scan_background(scan_id: str):
    """后台执行扫描任务"""
    try:
        db.update_scan_job(scan_id, status='scanning', started_at=time.time())

        # 获取所有概念对候选
        candidates = deduplicator.find_candidates()

        scanned = 0
        suggestions = []

        for candidate in candidates:
            # 分析候选对
            result = await deduplicator.analyze_pair(candidate)
            if result:
                suggestions.append(result)

            scanned += 1
            db.update_scan_job(scan_id, concepts_scanned=scanned)

        # 完成
        db.update_scan_job(
            scan_id,
            status='completed',
            suggestions=suggestions,
            completed_at=time.time()
        )
    except Exception as e:
        db.update_scan_job(scan_id, status='failed', error=str(e))
```

### 3.3 数据库改动

**文件**：`mkg/database.py`

#### 3.3.1 新增表结构

```sql
CREATE TABLE IF NOT EXISTS scan_jobs (
    id TEXT PRIMARY KEY,
    status TEXT DEFAULT 'pending',
    total_concepts INTEGER DEFAULT 0,
    concepts_scanned INTEGER DEFAULT 0,
    suggestions TEXT,  -- JSON
    error TEXT,
    created_at REAL,
    started_at REAL,
    completed_at REAL
)
```

#### 3.3.2 新增方法

```python
def create_scan_job(self, scan_id: str, total_concepts: int): ...
def get_scan_job(self, scan_id: str) -> dict | None: ...
def update_scan_job(self, scan_id: str, **kwargs): ...
```

### 3.4 API 层改动

**文件**：`frontend/src/lib/api.ts`

```typescript
dedupApi: {
  // 改造
  scan: () => api.post<{ scan_id: string; total_concepts: number; status: string }>('/concepts/dedup/scan'),

  // 新增
  scanStatus: (scanId: string) => api.get<ScanStatusResponse>(`/concepts/dedup/scan-status/${scanId}`),

  // 保持不变
  execute: (scanId: string, mergeIds: string[]) => ...
}
```

---

## 文件改动汇总

| 文件 | 改动类型 | 改动内容 |
|------|---------|---------|
| `frontend/src/pages/Papers.tsx` | 修改 | 上传提示自动消失、批量队列处理、预估时间显示 |
| `frontend/src/components/DedupPanel.tsx` | 修改 | 去重扫描进度、预估时间显示、轮询机制 |
| `frontend/src/lib/api.ts` | 修改 | 新增 `processOne`、`scanStatus` API |
| `backend/routes/papers.py` | 修改 | 新增 `process-one` API |
| `backend/routes/concepts.py` | 修改 | 扫描改为异步、新增 `scan-status` API |
| `mkg/database.py` | 修改 | 新增 `scan_jobs` 表和相关方法 |

---

## 实现顺序

1. **第一阶段**：PDF 上传提示自动消失（最简单，立即见效）
2. **第二阶段**：批量处理队列化（核心功能）
3. **第三阶段**：去重扫描预估时间（需要后端异步改造）

---

## 风险评估

- **低风险**：上传提示自动消失，纯前端改动
- **中风险**：批量处理队列化，需要前后端配合
- **中风险**：去重扫描异步化，需要数据库表变更