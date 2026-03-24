# 知识图谱功能增强实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance the knowledge graph system with optimized concept extraction prompts, batch PDF upload with parallel processing, and Obsidian markdown export.

**Architecture:** Backend uses FastAPI with SQLite; frontend uses React with TypeScript. Changes span across LLM prompt engineering, async batch processing, and export functionality.

**Tech Stack:** Python 3.10+, FastAPI, SQLite, React 18, TypeScript, Vite

---

## File Structure

### Modified Files
| File | Purpose |
|------|---------|
| `openclaw/pdf_parser.py` | Optimize concept extraction prompt |
| `backend/routes/papers.py` | Add batch upload/process endpoints |
| `backend/routes/graph.py` | Add Obsidian export endpoints |
| `backend/schemas.py` | Add batch-related Pydantic models |
| `openclaw/database.py` | Add batch_jobs table operations |
| `openclaw/obsidian_exporter.py` | Add export_overview method |
| `frontend/src/lib/api.ts` | Add batch and export API calls |
| `frontend/src/pages/Papers.tsx` | Add batch upload UI with progress |
| `frontend/src/pages/ConceptsGraph.tsx` | Add export button |

### Created Files
| File | Purpose |
|------|---------|
| None | All changes are modifications to existing files |

---

## Task 1: Optimize Concept Extraction Prompt

**Files:**
- Modify: `openclaw/pdf_parser.py:427-523`

- [ ] **Step 1: Update the `_build_extraction_prompt` method with optimized prompt**

Replace the `_build_extraction_prompt` method in `openclaw/pdf_parser.py` (lines 427-523) with:

```python
def _build_extraction_prompt(self, paper_content: PaperContent) -> str:
    """
    构建概念提取 Prompt - 优化版

    改进点：
    - 明确的层级定义和判断标准
    - Few-shot 示例引导
    - 自我验证机制
    """
    return f'''你是一名学术知识图谱构建助手。请从这篇论文中提取概念层级结构和研究信息。

**重要：所有概念名称必须使用中文！**

## 论文信息
标题：{paper_content.title}
作者：{', '.join(paper_content.authors[:3]) if paper_content.authors else 'Unknown'}
摘要：{paper_content.abstract[:500]}...

## 论文全文
{paper_content.full_text[:50000]}

## 概念层级定义

| 层级 | 英文 | 定义 | 判断标准 | 示例 |
|------|------|------|----------|------|
| 大领域 | field | 学科或研究领域 | 能否包含多个研究方向 | 人工智能、机器学习、运筹学 |
| 研究方向 | direction | 具体研究方向 | 是否有明确的研究目标或问题 | 强化学习、目标检测、车辆路径问题 |
| 方法 | method | 可执行的算法或方法 | 能否直接实现/执行 | 近端策略优化、A*算法、模拟退火 |
| 技术 | technique | 技术细节或组件 | 是否是方法的一部分或实现细节 | 梯度裁剪、注意力机制、值函数近似 |

**层级判断原则：**
1. 根节点应该是 field（大领域）
2. field 的子节点可以是 field 或 direction
3. direction 的子节点可以是 direction 或 method
4. method 的子节点通常是 technique
5. 层级深度建议 3-5 层

## Few-shot 示例

**输入论文：** 多智能体强化学习在无人机协同中的应用

**正确输出：**
```json
{{
  "concept_tree": {{
    "concept": "人工智能",
    "category": "field",
    "confidence": 0.95,
    "children": [
      {{
        "concept": "强化学习",
        "category": "direction",
        "confidence": 0.9,
        "children": [
          {{
            "concept": "多智能体强化学习",
            "category": "direction",
            "confidence": 0.85,
            "children": [
              {{
                "concept": "QMIX算法",
                "category": "method",
                "confidence": 0.8,
                "children": [
                  {{
                    "concept": "值函数分解",
                    "category": "technique",
                    "confidence": 0.75
                  }}
                ]
              }},
              {{
                "concept": "近端策略优化",
                "category": "method",
                "confidence": 0.8
              }}
            ]
          }}
        ]
      }},
      {{
        "concept": "无人机协同",
        "category": "direction",
        "confidence": 0.85
      }}
    ]
  }}
}}
```

## 提取要求

### 1. 提取研究问题（1-3 个）
论文试图解决什么核心问题？

### 2. 提取主要贡献（1-5 个）
论文的创新点是什么？

### 3. 构建概念层级树（核心任务）
从论文中提取概念，组织成树状层级结构。

**重要原则：**
- 根节点应该是最宏观的研究领域（如"人工智能"、"运筹学"）
- 子节点应该是更具体的研究方向、方法或技术
- 层级应该反映"包含关系"或"从属关系"
- 同一概念可以出现在不同分支下（如果论文涉及多个方向）
- **所有概念名称必须翻译成中文**
- 概念数量建议 5-15 个核心概念

### 4. 提取方法论
论文使用的核心方法是什么？

### 5. 提取数据集
论文使用了哪些数据集或实验环境？

### 6. 提取评估指标
论文使用了哪些评估指标？

## 自我验证清单

输出前请检查：
1. ✅ 概念数量是否合理（建议5-15个核心概念）？
2. ✅ 层级关系是否正确（子概念是否真正属于父概念）？
3. ✅ 是否有遗漏的核心概念？
4. ✅ 所有概念是否已翻译成中文？
5. ✅ 类别分配是否准确（field/direction/method/technique）？

## 输出格式

请输出严格的 JSON 格式：

```json
{{
    "title": "论文标题",
    "authors": ["作者1", "作者2"],
    "abstract": "摘要...",
    "research_questions": ["问题1", "问题2"],
    "contributions": ["贡献1", "贡献2"],
    "concept_tree": {{
        "concept": "根概念（中文）",
        "category": "field",
        "confidence": 0.95,
        "children": [
            {{
                "concept": "子概念（中文）",
                "category": "direction",
                "confidence": 0.9,
                "children": [...]
            }}
        ]
    }},
    "methodology": "方法描述",
    "datasets": ["数据集1", "数据集2"],
    "metrics": ["指标1", "指标2"]
}}
```

只输出 JSON，不要其他内容。所有概念名称必须使用中文！'''
```

- [ ] **Step 2: Verify the prompt file compiles**

Run: `cd D:/meta-knowledge-graph-main && python -c "from openclaw.pdf_parser import LLMConceptExtractor; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add openclaw/pdf_parser.py
git commit -m "$(cat <<'EOF'
feat(llm): optimize concept extraction prompt

- Add clear hierarchy definitions with judgment criteria
- Include few-shot example for better guidance
- Add self-verification checklist
- Improve prompt structure for better accuracy

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Add Batch-Related Schemas

**Files:**
- Modify: `backend/schemas.py`

- [ ] **Step 1: Add batch-related Pydantic models to `backend/schemas.py`**

Add after line 105 (after `SkillConceptSubmission` class):

```python
# Batch processing schemas
class BatchUploadResponse(BaseModel):
    """批量上传响应"""
    job_id: str
    uploaded: List[dict]
    total: int


class BatchProcessRequest(BaseModel):
    """批量处理请求"""
    job_id: str
    dois: List[str]


class BatchProcessResult(BaseModel):
    """单个论文处理结果"""
    doi: str
    status: str  # success, failed, pending
    concepts: Optional[int] = None
    error: Optional[str] = None


class BatchProcessResponse(BaseModel):
    """批量处理响应"""
    job_id: str
    status: str  # pending, processing, completed, failed
    total: int
    completed: int = 0
    successful: int = 0
    failed: int = 0
    results: List[BatchProcessResult] = []


class BatchJobStatus(BaseModel):
    """批量任务状态"""
    job_id: str
    status: str
    total: int
    completed: int
    successful: int
    failed: int
    created_at: Optional[str] = None


# Export schemas
class ExportResponse(BaseModel):
    """导出响应"""
    content: str
    stats: dict
```

- [ ] **Step 2: Verify schemas compile**

Run: `cd D:/meta-knowledge-graph-main && python -c "from backend.schemas import BatchUploadResponse, BatchProcessRequest, BatchProcessResponse; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/schemas.py
git commit -m "$(cat <<'EOF'
feat(schemas): add batch processing and export schemas

Add Pydantic models for:
- BatchUploadResponse
- BatchProcessRequest/Response
- BatchJobStatus
- ExportResponse

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Add Batch Jobs Table to Database

**Files:**
- Modify: `openclaw/database.py`

- [ ] **Step 1: Add batch_jobs table initialization in `_init_tables` method**

Add after line 122 (after the `concept_extractions` table creation):

```python
        # 批量任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_jobs (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total INTEGER,
                completed INTEGER DEFAULT 0,
                successful INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending'
            )
        """)
```

- [ ] **Step 2: Add batch job methods at the end of Database class**

Add before the `__enter__` method (around line 731):

```python
    # ========== 批量任务操作方法 ==========

    def create_batch_job(self, job_id: str, total: int):
        """创建批量任务"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO batch_jobs (id, total, status)
            VALUES (?, ?, 'pending')
        """, (job_id, total))
        self.conn.commit()

    def get_batch_job(self, job_id: str) -> Optional[dict]:
        """获取批量任务状态"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM batch_jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_batch_job(self, job_id: str, completed: int, successful: int, failed: int, status: str):
        """更新批量任务状态"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE batch_jobs
            SET completed = ?, successful = ?, failed = ?, status = ?
            WHERE id = ?
        """, (completed, successful, failed, status, job_id))
        self.conn.commit()
```

- [ ] **Step 3: Verify database module compiles**

Run: `cd D:/meta-knowledge-graph-main && python -c "from openclaw.database import Database; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add openclaw/database.py
git commit -m "$(cat <<'EOF'
feat(db): add batch_jobs table and methods

- Add batch_jobs table for tracking batch operations
- Add create_batch_job, get_batch_job, update_batch_job methods

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Add Batch Processing API Endpoints

**Files:**
- Modify: `backend/routes/papers.py`

- [ ] **Step 1: Add imports at the top of `backend/routes/papers.py`**

Add after line 11 (`import os`):

```python
import asyncio
import uuid
import time
```

- [ ] **Step 2: Add batch upload endpoint after the `upload_paper` function (after line 167)**

```python
@router.post("/batch-upload")
async def batch_upload_papers(files: List[UploadFile] = File(...)):
    """批量上传多个 PDF 文件"""
    project_root = Path(__file__).parent.parent.parent
    pending_dir = project_root / "papers" / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    job_id = f"batch_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    uploaded = []

    db = get_db()

    for file in files:
        if not file.filename or not file.filename.endswith('.pdf'):
            uploaded.append({
                "filename": file.filename or "unknown",
                "success": False,
                "error": "Invalid file type"
            })
            continue

        base_name = Path(file.filename).stem
        ext = Path(file.filename).suffix
        unique_name = f"{base_name}_{int(time.time())}_{uuid.uuid4().hex[:4]}{ext}"
        file_path = pending_dir / unique_name

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Parse PDF to get metadata
            parser = get_parser()
            content = parser.parse(str(file_path))

            if content and content.title:
                paper_data = {
                    'doi': base_name,
                    'title': content.title,
                    'abstract': content.abstract or "",
                    'authors': content.authors or [],
                    'pdf_path': str(file_path),
                }
            else:
                paper_data = {
                    'doi': base_name,
                    'title': base_name.replace('_', ' ').replace('-', ' '),
                    'abstract': "",
                    'authors': [],
                    'pdf_path': str(file_path),
                }

            doi = db.add_paper(paper_data)
            uploaded.append({
                "doi": doi,
                "title": paper_data['title'],
                "filename": file.filename,
                "status": "pending",
                "success": True
            })
        except Exception as e:
            uploaded.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })

    # Create batch job record
    successful_uploads = [u for u in uploaded if u.get('success')]
    db.create_batch_job(job_id, len(successful_uploads))

    return {
        "job_id": job_id,
        "uploaded": uploaded,
        "total": len([u for u in uploaded if u.get('success')])
    }
```

- [ ] **Step 3: Add batch process endpoint after batch upload**

```python
@router.post("/batch-process")
async def batch_process_papers(request: BatchProcessRequest):
    """并行处理多个论文"""
    db = get_db()
    parser = get_parser()
    extractor = get_extractor()

    if not extractor:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="LLM not configured")

    job = db.get_batch_job(request.job_id)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Batch job not found")

    # Update status to processing
    db.update_batch_job(request.job_id, 0, 0, 0, 'processing')

    results = []
    completed = 0
    successful = 0
    failed = 0

    async def process_single(doi: str) -> dict:
        nonlocal completed, successful, failed
        try:
            paper = db.get_paper(doi)
            if not paper or not paper.get('pdf_path'):
                return {"doi": doi, "status": "failed", "error": "Paper or PDF not found"}

            content = parser.parse(paper['pdf_path'])
            if not content:
                return {"doi": doi, "status": "failed", "error": "Failed to parse PDF"}

            extracted = extractor.extract(content)
            if extracted.concept_tree:
                graph = get_graph()
                graph.build_from_paper(doi, extracted.concept_tree.to_dict())
                db.save_concept_extraction(doi, extracted.concept_tree.to_dict(), extracted.raw_response)
                return {"doi": doi, "status": "success", "concepts": len(extracted.concept_tree.children) if extracted.concept_tree.children else 0}
            else:
                return {"doi": doi, "status": "failed", "error": "No concepts extracted"}
        except Exception as e:
            return {"doi": doi, "status": "failed", "error": str(e)}

    # Process papers concurrently (max 3 at a time to avoid overwhelming LLM)
    semaphore = asyncio.Semaphore(3)

    async def process_with_limit(doi: str):
        async with semaphore:
            result = await process_single(doi)
            completed += 1
            if result["status"] == "success":
                successful += 1
            else:
                failed += 1
            db.update_batch_job(request.job_id, completed, successful, failed,
                              'completed' if completed == len(request.dois) else 'processing')
            return result

    results = await asyncio.gather(*[process_with_limit(doi) for doi in request.dois])

    return {
        "job_id": request.job_id,
        "status": "completed",
        "total": len(request.dois),
        "completed": completed,
        "successful": successful,
        "failed": failed,
        "results": results
    }
```

- [ ] **Step 4: Add batch status endpoint**

```python
@router.get("/batch-status/{job_id}")
def get_batch_status(job_id: str):
    """获取批量任务状态"""
    db = get_db()
    job = db.get_batch_job(job_id)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Batch job not found")
    return job
```

- [ ] **Step 5: Update imports to include new schemas**

Update line 19 to include the new schemas:

```python
from backend.schemas import PaperResponse, PaperCreate, ProcessRequest, ProcessResponse, SkillConceptSubmission, BatchProcessRequest, BatchUploadResponse, BatchProcessResponse
```

- [ ] **Step 6: Verify papers route compiles**

Run: `cd D:/meta-knowledge-graph-main && python -c "from backend.routes.papers import router; print('OK')"`

Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add backend/routes/papers.py
git commit -m "$(cat <<'EOF'
feat(api): add batch upload and process endpoints

- Add POST /api/papers/batch-upload for multiple file upload
- Add POST /api/papers/batch-process for parallel LLM processing
- Add GET /api/papers/batch-status/{job_id} for status tracking
- Implement concurrent processing with semaphore limit

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Add Obsidian Export to Exporter

**Files:**
- Modify: `openclaw/obsidian_exporter.py`

- [ ] **Step 1: Add `export_overview` method to ObsidianExporter class**

Add after the `export_from_sqlite` method (around line 62):

```python
    def export_overview(self, db, graph) -> str:
        """导出图谱总览（单个Markdown文件）"""
        concepts = db.get_all_concepts()
        papers = db.get_all_papers()

        lines = []
        lines.append("# 知识图谱总览\n")
        lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 论文: {len(papers)} 篇 | 概念: {len(concepts)} 个\n")

        # Build parent map
        parent_map = {}
        for concept in concepts:
            parents = db.get_concept_parents(concept['id'])
            if parents:
                parent_map[concept['id']] = parents[0]['id']

        # Find root concepts (no parent)
        root_ids = [c['id'] for c in concepts if c['id'] not in parent_map]

        # Build children map
        children_map = {}
        for concept in concepts:
            children = db.get_concept_children(concept['id'])
            children_map[concept['id']] = [c['id'] for c in children]

        # Concept hierarchy section
        lines.append("## 概念层级\n")

        def format_tree(concept_id: str, indent: int = 0) -> List[str]:
            concept = next((c for c in concepts if c['id'] == concept_id), None)
            if not concept:
                return []
            result = []
            prefix = "  " * indent + "- " if indent > 0 else "### "
            result.append(f"{prefix}[[{concept['text']}]]\n")
            for child_id in children_map.get(concept_id, []):
                result.extend(format_tree(child_id, indent + 1 if indent > 0 else 1))
            return result

        for root_id in root_ids[:10]:  # Limit to 10 root concepts
            lines.extend(format_tree(root_id))

        lines.append("\n## 概念详情\n")

        # Concept details
        for concept in concepts[:50]:  # Limit details
            lines.append(f"### {concept['text']}\n")
            lines.append(f"- **类别**: {concept.get('category', 'method')}\n")
            lines.append(f"- **关联论文**: {concept.get('paper_count', 0)} 篇\n")

            # Children
            children = children_map.get(concept['id'], [])
            if children:
                child_texts = []
                for child_id in children:
                    child = next((c for c in concepts if c['id'] == child_id), None)
                    if child:
                        child_texts.append(f"[[{child['text']}]]")
                lines.append(f"- **子概念**: {', '.join(child_texts)}\n")

            # Parents
            parent_id = parent_map.get(concept['id'])
            if parent_id:
                parent = next((c for c in concepts if c['id'] == parent_id), None)
                if parent:
                    lines.append(f"- **父概念**: [[{parent['text']}]]\n")

            lines.append("\n")

        return "".join(lines)
```

- [ ] **Step 2: Verify exporter compiles**

Run: `cd D:/meta-knowledge-graph-main && python -c "from openclaw.obsidian_exporter import ObsidianExporter; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add openclaw/obsidian_exporter.py
git commit -m "$(cat <<'EOF'
feat(export): add export_overview method for single-file markdown export

- Export all concepts with hierarchy in Obsidian-compatible format
- Use [[double-link]] syntax for concept relationships
- Include concept details with category and paper count

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Add Export API Endpoints

**Files:**
- Modify: `backend/routes/graph.py`

- [ ] **Step 1: Add imports at the top**

Add after line 14:

```python
from fastapi import Response
from openclaw.obsidian_exporter import ObsidianExporter
from backend.schemas import ExportResponse
from datetime import datetime
```

- [ ] **Step 2: Add export endpoints after existing routes**

Add after the `get_tree_data` function:

```python
@router.get("/export/obsidian")
def export_obsidian():
    """导出知识图谱为 Obsidian 兼容的 Markdown 格式"""
    db = get_db()
    graph = get_graph()

    exporter = ObsidianExporter()
    content = exporter.export_overview(db, graph)

    stats = db.get_stats()

    return ExportResponse(
        content=content,
        stats={
            "papers": stats.get('papers', {}).get('total', 0),
            "concepts": stats.get('concepts', {}).get('total', 0),
            "generated_at": datetime.now().isoformat()
        }
    )


@router.get("/export/obsidian/download")
def download_obsidian():
    """下载 Obsidian Markdown 文件"""
    db = get_db()
    graph = get_graph()

    exporter = ObsidianExporter()
    content = exporter.export_overview(db, graph)

    return Response(
        content=content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename=knowledge-graph-{datetime.now().strftime('%Y%m%d')}.md"
        }
    )
```

- [ ] **Step 3: Verify graph route compiles**

Run: `cd D:/meta-knowledge-graph-main && python -c "from backend.routes.graph import router; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/routes/graph.py
git commit -m "$(cat <<'EOF'
feat(api): add Obsidian export endpoints

- Add GET /api/graph/export/obsidian for content
- Add GET /api/graph/export/obsidian/download for file download

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Update Frontend API Client

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add batch and export API methods**

Add after the `dedupApi` object (after line 79):

```typescript
// Batch API
export const batchApi = {
  upload: (files: File[]) => {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    return api.post<BatchUploadResponse>('/papers/batch-upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  process: (jobId: string, dois: string[]) =>
    api.post<BatchProcessResponse>('/papers/batch-process', { job_id: jobId, dois }),
  status: (jobId: string) =>
    api.get<BatchJobStatus>(`/papers/batch-status/${jobId}`),
}

// Export API
export const exportApi = {
  obsidian: () => api.get<ExportResponse>('/graph/export/obsidian'),
  download: () =>
    api.get('/graph/export/obsidian/download', { responseType: 'blob' }),
}

// Batch types
interface BatchUploadResponse {
  job_id: string
  uploaded: Array<{
    doi?: string
    title?: string
    filename: string
    status?: string
    success: boolean
    error?: string
  }>
  total: number
}

interface BatchProcessResponse {
  job_id: string
  status: string
  total: number
  completed: number
  successful: number
  failed: number
  results: Array<{
    doi: string
    status: string
    concepts?: number
    error?: string
  }>
}

interface BatchJobStatus {
  job_id: string
  status: string
  total: number
  completed: number
  successful: number
  failed: number
  created_at?: string
}

interface ExportResponse {
  content: string
  stats: {
    papers: number
    concepts: number
    generated_at: string
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd D:/meta-knowledge-graph-main/frontend && npx tsc --noEmit`

Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "$(cat <<'EOF'
feat(frontend): add batch and export API methods

- Add batchApi for batch upload/process/status
- Add exportApi for Obsidian export
- Add TypeScript interfaces for responses

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Add Batch Upload UI to Papers Page

**Files:**
- Modify: `frontend/src/pages/Papers.tsx`

- [ ] **Step 1: Update imports**

Replace line 2 with:

```typescript
import { Upload, FileText, Trash2, Play, RefreshCw, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { papersApi, batchApi } from '../lib/api'
```

- [ ] **Step 2: Add batch processing state**

Add after `const fileInputRef = useRef<HTMLInputElement>(null)`:

```typescript
  const [batchProcessing, setBatchProcessing] = useState(false)
  const [batchProgress, setBatchProgress] = useState<{
    total: number
    completed: number
    successful: number
    failed: number
  } | null>(null)
```

- [ ] **Step 3: Add batch process handler**

Add after `handleUpload` function:

```typescript
  const handleBatchProcess = async () => {
    const pendingPapers = papers.filter(p => p.status === 'pending')
    if (pendingPapers.length === 0) {
      alert('没有待处理的论文')
      return
    }

    if (!confirm(`确定要处理 ${pendingPapers.length} 篇论文？\n这可能需要一些时间。`)) {
      return
    }

    setBatchProcessing(true)
    setBatchProgress({ total: pendingPapers.length, completed: 0, successful: 0, failed: 0 })

    try {
      // First upload to create batch job (if needed)
      const dois = pendingPapers.map(p => p.doi)

      // Process directly
      const res = await batchApi.process(`manual_${Date.now()}`, dois)

      setBatchProgress({
        total: res.data.total,
        completed: res.data.completed,
        successful: res.data.successful,
        failed: res.data.failed,
      })

      loadPapers()
    } catch (err: any) {
      alert(err.response?.data?.detail || '批量处理失败')
    } finally {
      setBatchProcessing(false)
    }
  }
```

- [ ] **Step 4: Add batch process button and progress UI**

Replace the button section in the header (lines 127-148) with:

```typescriptx
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">论文管理</h1>
        <div className="flex gap-4">
          <button
            onClick={() => loadPapers()}
            className="flex items-center px-4 py-2 border rounded-lg hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </button>
          {papers.filter(p => p.status === 'pending').length > 0 && (
            <button
              onClick={handleBatchProcess}
              disabled={batchProcessing}
              className="flex items-center px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
            >
              {batchProcessing ? (
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
          <label className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-lg cursor-pointer hover:bg-blue-600">
            <Upload className="h-4 w-4 mr-2" />
            {uploading ? '上传中...' : '上传 PDF'}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              multiple
              className="hidden"
              onChange={handleUpload}
              disabled={uploading}
            />
          </label>
        </div>
      </div>

      {/* Batch Progress */}
      {batchProgress && (
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="font-medium mb-3">批量处理进度</h3>
          <div className="flex items-center gap-4">
            <div className="flex-1 bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-green-500 h-2.5 rounded-full transition-all"
                style={{ width: `${(batchProgress.completed / batchProgress.total) * 100}%` }}
              />
            </div>
            <span className="text-sm text-gray-600">
              {batchProgress.completed}/{batchProgress.total}
            </span>
          </div>
          <div className="flex gap-4 mt-2 text-sm">
            <span className="text-green-600">成功: {batchProgress.successful}</span>
            <span className="text-red-600">失败: {batchProgress.failed}</span>
          </div>
        </div>
      )}
```

- [ ] **Step 5: Verify frontend compiles**

Run: `cd D:/meta-knowledge-graph-main/frontend && npx tsc --noEmit`

Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Papers.tsx
git commit -m "$(cat <<'EOF'
feat(frontend): add batch processing UI to Papers page

- Add batch process button for pending papers
- Show progress bar during batch processing
- Display success/failure counts

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Add Export Button to Concepts Page

**Files:**
- Modify: `frontend/src/pages/ConceptsGraph.tsx`

- [ ] **Step 1: Add import**

Add after line 5:

```typescript
import { exportApi } from '../lib/api'
import { Download } from 'lucide-react'
```

- [ ] **Step 2: Add export handler**

Add after `handleDiscoverResearchPoints` function:

```typescript
  const handleExport = useCallback(async () => {
    try {
      const res = await exportApi.download()
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `knowledge-graph-${new Date().toISOString().split('T')[0]}.md`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export failed:', err)
      alert('导出失败')
    }
  }, [])
```

- [ ] **Step 3: Add export button next to dedup button**

Replace the dedup button section (lines 494-502) with:

```typescriptx
      {/* Action Buttons */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        <button
          onClick={handleExport}
          className="flex items-center gap-2 px-4 py-2 bg-white/90 backdrop-blur rounded-xl shadow-lg text-sm font-medium text-gray-700 hover:bg-white transition-colors"
        >
          <Download className="h-4 w-4" />
          导出
        </button>
        <button
          onClick={() => setDedupOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-white/90 backdrop-blur rounded-xl shadow-lg text-sm font-medium text-gray-700 hover:bg-white transition-colors"
        >
          🔄 去重扫描
        </button>
      </div>
```

- [ ] **Step 4: Verify frontend compiles**

Run: `cd D:/meta-knowledge-graph-main/frontend && npx tsc --noEmit`

Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ConceptsGraph.tsx
git commit -m "$(cat <<'EOF'
feat(frontend): add Obsidian export button to Concepts page

- Add export button that downloads markdown file
- Place export button next to dedup scan button

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Final Integration Test

**Files:**
- None (testing only)

- [ ] **Step 1: Start backend server**

Run: `cd D:/meta-knowledge-graph-main && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8088 --reload &`

- [ ] **Step 2: Start frontend server**

Run: `cd D:/meta-knowledge-graph-main/frontend && npm run dev &`

- [ ] **Step 3: Verify all endpoints are accessible**

Run: `curl http://localhost:8088/docs`

Expected: Swagger UI loads with new endpoints visible

- [ ] **Step 4: Test batch upload endpoint**

Run: `curl -X POST "http://localhost:8088/api/papers/batch-upload" -F "files=@test.pdf"`

Expected: Returns job_id and uploaded files list

- [ ] **Step 5: Test export endpoint**

Run: `curl "http://localhost:8088/api/graph/export/obsidian"`

Expected: Returns markdown content with concept hierarchy

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat: complete feature enhancements for knowledge graph

Features implemented:
1. Optimized concept extraction prompt with few-shot examples
2. Batch PDF upload with parallel LLM processing
3. Obsidian markdown export functionality

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Summary

This plan implements three major features:

1. **Prompt Optimization** - Enhanced LLM prompt with clear hierarchy definitions, few-shot examples, and self-verification
2. **Batch Processing** - Backend endpoints for batch upload and parallel processing with progress tracking
3. **Obsidian Export** - Single-file markdown export with [[double-link]] syntax for concept relationships

Each task is designed to be completed independently with frequent commits for easy rollback.