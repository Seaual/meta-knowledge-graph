# Concept Extraction and Folder Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optimize concept extraction to match existing concepts, add folder management for papers, and clean up orphaned nodes when deleting papers.

**Architecture:** Add existing concept context to LLM prompt → Database schema for folders → Backend API for folder CRUD → Frontend folder navigation with paper contribution display → Cascade delete for paper removal.

**Tech Stack:** Python, FastAPI, SQLite, React, TypeScript, TailwindCSS

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `openclaw/graph.py` | Modify | Add `get_concept_tree_summary()` |
| `openclaw/pdf_parser.py` | Modify | Update `_build_extraction_prompt()` with existing concepts |
| `openclaw/database.py` | Modify | Add folders table and methods |
| `backend/routes/papers.py` | Modify | Add folder filter, contribution endpoint, cascade delete |
| `backend/routes/folders.py` | Create | Folder CRUD endpoints |
| `backend/schemas.py` | Modify | Add folder schemas |
| `backend/main.py` | Modify | Register folders router |
| `frontend/src/lib/api.ts` | Modify | Add foldersApi, update papersApi |
| `frontend/src/components/CreateFolderModal.tsx` | Create | Folder creation modal |
| `frontend/src/pages/Papers.tsx` | Modify | Add folder sidebar, contribution columns |
| `frontend/src/pages/ConceptsGraph.tsx` | Modify | Add folder selector |

---

## Task 1: Add `get_concept_tree_summary()` to graph.py

**Files:**
- Modify: `openclaw/graph.py`

- [ ] **Step 1: Add method to return simplified concept tree**

Add after the `__init__` method in the `KnowledgeGraph` class:

```python
def get_concept_tree_summary(self, max_depth: int = 3) -> str:
    """
    获取概念树的简化文本表示，用于 LLM prompt

    Args:
        max_depth: 最大深度限制

    Returns:
        概念树的缩进文本表示
    """
    roots = self.db.get_root_concepts()
    if not roots:
        return "（图谱为空）"

    lines = []

    def build_tree(concept_id: str, depth: int, prefix: str = ""):
        if depth > max_depth:
            return

        concept = self.db.get_concept(concept_id)
        if not concept:
            return

        indent = "  " * depth
        lines.append(f"{indent}- {concept['text']}")

        children = self.db.get_concept_children(concept_id)
        for child in children[:10]:  # Limit children per node
            build_tree(child['id'], depth + 1)

    for root in roots[:5]:  # Limit root concepts
        build_tree(root['id'], 0)

    return "\n".join(lines)
```

- [ ] **Step 2: Commit**

```bash
git add openclaw/graph.py
git commit -m "feat(graph): add get_concept_tree_summary for LLM context"
```

---

## Task 2: Update `_build_extraction_prompt()` with existing concepts

**Files:**
- Modify: `openclaw/pdf_parser.py`

- [ ] **Step 1: Modify method signature**

Find the `_build_extraction_prompt` method (around line 427) and change the signature:

```python
def _build_extraction_prompt(self, paper_content: PaperContent, existing_concepts: str = "") -> str:
```

- [ ] **Step 2: Add existing concepts section to prompt**

Find the line `return f"""` and add the existing concepts section after `## 论文全文` section:

```python
        return f"""
你是一名学术知识图谱构建助手。请从这篇论文中提取概念层级结构和研究信息。

**重要：所有概念名称必须使用中文！**

## 论文信息
标题：{paper_content.title}
作者：{', '.join(paper_content.authors[:3]) if paper_content.authors else 'Unknown'}
摘要：{paper_content.abstract[:500]}...

## 论文全文
{paper_content.full_text[:50000]}

{self._build_existing_concepts_section(existing_concepts)}

---
```

- [ ] **Step 3: Add helper method**

Add this helper method after `_build_extraction_prompt`:

```python
def _build_existing_concepts_section(self, existing_concepts: str) -> str:
    """构建已有概念参考部分"""
    if not existing_concepts or existing_concepts == "（图谱为空）":
        return ""

    return f"""---

## 已有概念树（参考）

当前知识图谱中已有以下概念结构，新概念请尽量归类到合适的位置：

{existing_concepts}

**重要规则：**
1. 如果新提取的概念已存在于上述树中，请使用相同的概念名和正确的父节点路径
2. 如果新概念是已有概念的子概念，请放在正确位置（如"卷积神经网络"应放在"人工智能→机器学习→深度学习"下）
3. 只有当概念确实是新的研究领域时，才创建新的根概念
"""
```

- [ ] **Step 4: Update `extract` method signature**

Find the `extract` method (around line 415) and update it:

```python
def extract(self, paper_content: PaperContent, existing_concepts: str = "") -> LLMExtractedContent:
    """
    提取论文内容

    Args:
        paper_content: 论文内容
        existing_concepts: 已有概念树（用于智能匹配）
    """
    prompt = self._build_extraction_prompt(paper_content, existing_concepts)
```

- [ ] **Step 5: Commit**

```bash
git add openclaw/pdf_parser.py
git commit -m "feat(pdf_parser): add existing concepts context to extraction prompt"
```

---

## Task 3: Update `process_paper()` to pass existing concepts

**Files:**
- Modify: `backend/routes/papers.py`

- [ ] **Step 1: Import KnowledgeGraph**

Add to the imports (around line 20):

```python
from openclaw.graph import KnowledgeGraph
```

- [ ] **Step 2: Modify `process_paper()` function**

Find the `process_paper` function (around line 386) and modify it:

```python
@router.post("/process", response_model=ProcessResponse)
def process_paper(request: ProcessRequest):
    """Process a paper with LLM extraction"""
    db = get_db()
    paper = db.get_paper(request.doi)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    pdf_path = paper.get('pdf_path')
    if not pdf_path or not Path(pdf_path).exists():
        raise HTTPException(status_code=400, detail="PDF file not found")

    # Get LLM extractor
    extractor = get_extractor()
    if not extractor:
        raise HTTPException(status_code=400, detail="LLM not configured. Claude CLI or API Key required.")

    # Get existing concepts for smart matching
    graph = KnowledgeGraph(db)
    existing_concepts = graph.get_concept_tree_summary()

    # Parse and extract
    parser = get_parser()
    content = parser.parse(pdf_path)

    if not content:
        raise HTTPException(status_code=400, detail="Failed to parse PDF")

    try:
        extracted = extractor.extract(content, existing_concepts)
        concept_tree = extracted.concept_tree.to_dict() if extracted.concept_tree else None
```

- [ ] **Step 3: Commit**

```bash
git add backend/routes/papers.py
git commit -m "feat(papers): pass existing concepts to extraction for smart matching"
```

---

## Task 4: Add folders table and methods to database.py

**Files:**
- Modify: `openclaw/database.py`

- [ ] **Step 1: Add folders table to `_init_tables`**

Find the `_init_tables` method and add after the `batch_jobs` table (around line 135):

```python
        # 文件夹表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                paper_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
```

- [ ] **Step 2: Add folder_id column to papers table**

Add after the folders table:

```python
        # 添加 folder_id 列（如果不存在）
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN folder_id TEXT DEFAULT 'default'")
        except:
            pass  # Column already exists
```

- [ ] **Step 3: Add folder CRUD methods at the end of Database class**

Add before the context manager methods:

```python
    # ========== 文件夹操作方法 ==========

    def get_all_folders(self) -> list:
        """获取所有文件夹"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM folders ORDER BY created_at")
        return [dict(row) for row in cursor.fetchall()]

    def get_folder(self, folder_id: str) -> Optional[dict]:
        """获取单个文件夹"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM folders WHERE id = ?", (folder_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def create_folder(self, folder_data: dict) -> str:
        """创建文件夹"""
        cursor = self.conn.cursor()
        folder_id = self._to_slug(folder_data['name'])
        cursor.execute("""
            INSERT OR IGNORE INTO folders (id, name, description)
            VALUES (?, ?, ?)
        """, (folder_id, folder_data['name'], folder_data.get('description')))
        self.conn.commit()
        return folder_id

    def update_folder(self, folder_id: str, data: dict):
        """更新文件夹"""
        cursor = self.conn.cursor()
        if 'name' in data:
            cursor.execute("UPDATE folders SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                          (data['name'], folder_id))
        if 'description' in data:
            cursor.execute("UPDATE folders SET description = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                          (data['description'], folder_id))
        self.conn.commit()

    def delete_folder(self, folder_id: str) -> bool:
        """删除文件夹（论文移到 default）"""
        if folder_id == 'default':
            return False  # 不能删除默认文件夹

        cursor = self.conn.cursor()
        # 将论文移到 default
        cursor.execute("UPDATE papers SET folder_id = 'default' WHERE folder_id = ?", (folder_id,))
        # 删除文件夹
        cursor.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        self.conn.commit()
        return True

    def ensure_default_folder(self):
        """确保默认文件夹存在"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM folders WHERE id = 'default'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO folders (id, name, description)
                VALUES ('default', '默认', '默认文件夹')
            """)
            self.conn.commit()

    def get_papers_by_folder(self, folder_id: str) -> list:
        """按文件夹获取论文"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE folder_id = ? ORDER BY created_at DESC", (folder_id,))
        papers = [dict(row) for row in cursor.fetchall()]
        for paper in papers:
            if paper.get('authors') and isinstance(paper['authors'], str):
                try:
                    paper['authors'] = json.loads(paper['authors'])
                except:
                    paper['authors'] = []
            if paper.get('keywords') and isinstance(paper['keywords'], str):
                try:
                    paper['keywords'] = json.loads(paper['keywords'])
                except:
                    paper['keywords'] = []
            if paper.get('contributions') and isinstance(paper['contributions'], str):
                try:
                    paper['contributions'] = json.loads(paper['contributions'])
                except:
                    paper['contributions'] = []
        return papers

    def move_paper_to_folder(self, doi: str, folder_id: str):
        """移动论文到文件夹"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE papers SET folder_id = ? WHERE doi = ?", (folder_id, doi))
        self.conn.commit()

    def get_paper_contribution(self, doi: str) -> dict:
        """获取论文贡献的概念节点数和根概念"""
        cursor = self.conn.cursor()

        # 获取该论文关联的概念数
        cursor.execute("""
            SELECT COUNT(*) as count FROM paper_concepts WHERE paper_doi = ?
        """, (doi,))
        node_count = cursor.fetchone()['count']

        # 获取根概念（该论文的概念树的根）
        cursor.execute("""
            SELECT c.text FROM concepts c
            JOIN paper_concepts pc ON c.id = pc.concept_id
            LEFT JOIN concept_relations cr ON c.id = cr.child_id
            WHERE pc.paper_doi = ? AND cr.parent_id IS NULL
            LIMIT 1
        """, (doi,))
        row = cursor.fetchone()
        root_concept = row['text'] if row else None

        return {"node_count": node_count, "root_concept": root_concept}
```

- [ ] **Step 4: Call ensure_default_folder in connect method**

Find the `connect` method and add after `_init_tables()`:

```python
        self._init_tables()
        self.ensure_default_folder()  # 确保默认文件夹存在
```

- [ ] **Step 5: Commit**

```bash
git add openclaw/database.py
git commit -m "feat(database): add folders table and CRUD methods"
```

---

## Task 5: Add folder schemas to schemas.py

**Files:**
- Modify: `backend/schemas.py`

- [ ] **Step 1: Add folder schemas at the end of file**

```python
# Folder schemas
class FolderBase(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    paper_count: int = 0


class FolderCreate(BaseModel):
    name: str
    description: Optional[str] = None


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class FolderResponse(FolderBase):
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class PaperContribution(BaseModel):
    """论文贡献信息"""
    node_count: int
    root_concept: Optional[str] = None


class PaperWithContribution(PaperResponse):
    """带贡献信息的论文响应"""
    node_count: int = 0
    root_concept: Optional[str] = None
```

- [ ] **Step 2: Commit**

```bash
git add backend/schemas.py
git commit -m "feat(schemas): add folder and paper contribution schemas"
```

---

## Task 6: Create folder routes

**Files:**
- Create: `backend/routes/folders.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create `backend/routes/folders.py`**

```python
"""
Folder API routes
"""

from fastapi import APIRouter, HTTPException
from typing import List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from openclaw.database import Database
from backend.schemas import FolderResponse, FolderCreate, FolderUpdate

router = APIRouter(prefix="/api/folders", tags=["folders"])

_db = None


def get_db():
    global _db
    if _db is None:
        _db = Database("openclaw.db")
        _db.connect()
    return _db


@router.get("/", response_model=List[FolderResponse])
def list_folders():
    """获取所有文件夹"""
    db = get_db()
    folders = db.get_all_folders()

    # 计算每个文件夹的论文数
    for folder in folders:
        papers = db.get_papers_by_folder(folder['id'])
        folder['paper_count'] = len(papers)

    return folders


@router.post("/", response_model=FolderResponse)
def create_folder(request: FolderCreate):
    """创建文件夹"""
    db = get_db()
    folder_id = db.create_folder(request.model_dump())
    folder = db.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=500, detail="Failed to create folder")
    folder['paper_count'] = 0
    return folder


@router.patch("/{folder_id}", response_model=FolderResponse)
def update_folder(folder_id: str, request: FolderUpdate):
    """更新文件夹"""
    db = get_db()
    folder = db.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    db.update_folder(folder_id, request.model_dump(exclude_none=True))
    folder = db.get_folder(folder_id)
    papers = db.get_papers_by_folder(folder_id)
    folder['paper_count'] = len(papers)
    return folder


@router.delete("/{folder_id}")
def delete_folder(folder_id: str):
    """删除文件夹（论文移到 default）"""
    db = get_db()

    if folder_id == 'default':
        raise HTTPException(status_code=400, detail="Cannot delete default folder")

    folder = db.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    success = db.delete_folder(folder_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete folder")

    return {"success": True, "message": "Folder deleted, papers moved to default"}
```

- [ ] **Step 2: Register router in `backend/main.py`**

Add import (around line 16):

```python
from backend.routes import papers, concepts, graph, llm, folders
```

Add router registration (around line 37):

```python
app.include_router(folders.router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/routes/folders.py backend/main.py
git commit -m "feat(backend): add folder CRUD API routes"
```

---

## Task 7: Update papers routes with folder support

**Files:**
- Modify: `backend/routes/papers.py`

- [ ] **Step 1: Update `list_papers` to support folder filter**

Find the `list_papers` function and modify:

```python
@router.get("/", response_model=List[PaperResponse])
def list_papers(status: Optional[str] = None, folder: Optional[str] = None):
    """Get all papers or filter by status/folder"""
    db = get_db()

    if folder:
        papers = db.get_papers_by_folder(folder)
        if status:
            papers = [p for p in papers if p.get('status') == status]
    elif status:
        papers = db.get_papers_by_status(status)
    else:
        papers = db.get_all_papers()
    return papers
```

- [ ] **Step 2: Update `upload_paper` to accept folder**

Find the `upload_paper` function and modify:

```python
@router.post("/upload")
async def upload_paper(file: UploadFile = File(...), folder: str = Form("default")):
    """Upload a PDF file to pending folder"""
    import os

    # Create papers directory structure
    project_root = Path(__file__).parent.parent.parent
    pending_dir = project_root / "papers" / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    # ... rest of the function remains the same until the end ...

    # Update paper with folder
    if folder != "default":
        db.move_paper_to_folder(doi, folder)

    return {
        "success": True,
        "doi": doi,
        "title": paper_data['title'],
        "pdf_path": str(file_path),
        "message": "Paper uploaded to pending folder",
        "folder": folder
    }
```

- [ ] **Step 3: Add move paper endpoint**

Add after the `delete_paper` function:

```python
@router.patch("/{doi:path}/folder")
def move_paper(doi: str, request: dict):
    """Move paper to a different folder"""
    db = get_db()
    paper = db.get_paper(doi)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    folder_id = request.get('folder_id', 'default')
    folder = db.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    db.move_paper_to_folder(doi, folder_id)
    return {"success": True, "message": f"Paper moved to {folder['name']}"}


@router.get("/{doi:path}/contribution")
def get_paper_contribution(doi: str):
    """Get paper's concept contribution"""
    db = get_db()
    paper = db.get_paper(doi)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    return db.get_paper_contribution(doi)
```

- [ ] **Step 4: Commit**

```bash
git add backend/routes/papers.py
git commit -m "feat(papers): add folder filter, upload to folder, and contribution endpoint"
```

---

## Task 8: Add cascade delete for papers

**Files:**
- Modify: `openclaw/database.py`
- Modify: `backend/routes/papers.py`

- [ ] **Step 1: Add `delete_paper_cascade` method to Database class**

Add after the `get_paper_contribution` method:

```python
def delete_paper_cascade(self, doi: str):
    """
    删除论文及其孤立的概念节点

    工作流程：
    1. 获取该论文关联的所有概念
    2. 删除 paper_concepts 关联
    3. 对每个概念，检查是否有其他论文引用
    4. 如果没有，删除该概念并递归检查子概念
    5. 清理 concept_relations 记录
    """
    cursor = self.conn.cursor()

    # 获取该论文关联的概念
    cursor.execute("""
        SELECT concept_id FROM paper_concepts WHERE paper_doi = ?
    """, (doi,))
    concepts = [row['concept_id'] for row in cursor.fetchall()]

    # 删除 paper_concepts 关联
    cursor.execute("DELETE FROM paper_concepts WHERE paper_doi = ?", (doi,))

    # 删除 concept_extractions
    cursor.execute("DELETE FROM concept_extractions WHERE paper_doi = ?", (doi,))

    # 删除 processing_log
    cursor.execute("DELETE FROM processing_log WHERE paper_doi = ?", (doi,))

    # 检查并删除孤立概念
    for concept_id in concepts:
        self._delete_orphaned_concept(concept_id)

    # 删除论文
    cursor.execute("DELETE FROM papers WHERE doi = ?", (doi,))

    self.conn.commit()


def _delete_orphaned_concept(self, concept_id: str):
    """递归删除孤立概念（没有论文引用的概念）"""
    cursor = self.conn.cursor()

    # 检查是否有其他论文引用此概念
    cursor.execute("""
        SELECT COUNT(*) as count FROM paper_concepts WHERE concept_id = ?
    """, (concept_id,))

    if cursor.fetchone()['count'] > 0:
        return  # 还有论文引用，不删除

    # 获取子概念
    cursor.execute("""
        SELECT child_id FROM concept_relations WHERE parent_id = ?
    """, (concept_id,))
    children = [row['child_id'] for row in cursor.fetchall()]

    # 删除与父概念的关系
    cursor.execute("DELETE FROM concept_relations WHERE child_id = ?", (concept_id,))

    # 删除概念本身
    cursor.execute("DELETE FROM concepts WHERE id = ?", (concept_id,))

    # 递归检查子概念
    for child_id in children:
        self._delete_orphaned_concept(child_id)
```

- [ ] **Step 2: Update `delete_paper` in papers.py**

Find the `delete_paper` function and replace with:

```python
@router.delete("/{doi:path}")
def delete_paper(doi: str):
    """Delete a paper and its orphaned concepts"""
    db = get_db()
    paper = db.get_paper(doi)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # Delete PDF file if exists
    pdf_path = paper.get('pdf_path')
    if pdf_path and Path(pdf_path).exists():
        Path(pdf_path).unlink()

    # Use cascade delete
    db.delete_paper_cascade(doi)

    return {"success": True, "message": "Paper and orphaned concepts deleted"}
```

- [ ] **Step 3: Commit**

```bash
git add openclaw/database.py backend/routes/papers.py
git commit -m "feat: add cascade delete for papers with orphaned concepts"
```

---

## Task 9: Add frontend API client for folders

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add folder types and API**

Add at the end of `frontend/src/lib/api.ts`:

```typescript
// Folder types
interface FolderResponse {
  id: string
  name: string
  description?: string
  paper_count: number
  created_at?: string
}

interface CreateFolderRequest {
  name: string
  description?: string
}

interface UpdateFolderRequest {
  name?: string
  description?: string
}

interface PaperContribution {
  node_count: number
  root_concept?: string
}

// Folder API
export const foldersApi = {
  list: () => api.get<FolderResponse[]>('/folders/'),
  create: (data: CreateFolderRequest) => api.post<FolderResponse>('/folders/', data),
  update: (id: string, data: UpdateFolderRequest) => api.patch<FolderResponse>(`/folders/${id}`, data),
  delete: (id: string) => api.delete(`/folders/${id}`),
}
```

- [ ] **Step 2: Update papersApi**

Modify the `papersApi` in the same file:

```typescript
// Papers API
export const papersApi = {
  list: (status?: string, folder?: string) => api.get('/papers/', { params: { status, folder } }),
  get: (doi: string) => api.get(`/papers/${encodeURIComponent(doi)}`),
  upload: (file: File, folder?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (folder) formData.append('folder', folder)
    return api.post('/papers/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  process: (doi: string) => api.post('/papers/process', { doi }),
  delete: (doi: string) => api.delete(`/papers/${encodeURIComponent(doi)}`),
  move: (doi: string, folderId: string) => api.patch(`/papers/${encodeURIComponent(doi)}/folder`, { folder_id: folderId }),
  contribution: (doi: string) => api.get<PaperContribution>(`/papers/${encodeURIComponent(doi)}/contribution`),
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat(frontend): add foldersApi and update papersApi"
```

---

## Task 10: Create CreateFolderModal component

**Files:**
- Create: `frontend/src/components/CreateFolderModal.tsx`

- [ ] **Step 1: Create the modal component**

```tsx
import { useState } from 'react'
import { X } from 'lucide-react'

interface Props {
  onClose: () => void
  onCreate: (name: string, description: string) => void
}

export default function CreateFolderModal({ onClose, onCreate }: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    onCreate(name.trim(), description.trim())
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">新建文件夹</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              文件夹名称 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="例如：强化学习论文"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              描述（可选）
            </label>
            <input
              type="text"
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="文件夹描述"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </form>

        <div className="flex gap-2 p-4 border-t bg-gray-50">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2 px-4 rounded-lg border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-100"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={!name.trim()}
            className="flex-1 py-2 px-4 rounded-lg bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            创建
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/CreateFolderModal.tsx
git commit -m "feat(frontend): add CreateFolderModal component"
```

---

## Task 11: Update Papers.tsx with folder sidebar

**Files:**
- Modify: `frontend/src/pages/Papers.tsx`

- [ ] **Step 1: Update imports**

```tsx
import { useEffect, useState, useRef } from 'react'
import { Upload, FileText, Trash2, Play, RefreshCw, CheckCircle, XCircle, Loader2, FolderPlus, Folder, MoreVertical, Nodes } from 'lucide-react'
import { papersApi, batchApi, foldersApi } from '../lib/api'
import CreateFolderModal from '../components/CreateFolderModal'
```

- [ ] **Step 2: Add folder state and load function**

Add after the existing state declarations:

```tsx
const [folders, setFolders] = useState<{id: string, name: string, paper_count: number}[]>([])
const [activeFolder, setActiveFolder] = useState('default')
const [showCreateFolder, setShowCreateFolder] = useState(false)
const [contributions, setContributions] = useState<Record<string, {node_count: number, root_concept?: string}>>({})
```

- [ ] **Step 3: Add loadFolders function**

Add after `loadPapers`:

```tsx
const loadFolders = () => {
  foldersApi.list().then(res => {
    setFolders(res.data)
  })
}

const loadContributions = async (paperList: Paper[]) => {
  const results: Record<string, {node_count: number, root_concept?: string}> = {}
  for (const paper of paperList) {
    if (paper.status === 'processed') {
      try {
        const res = await papersApi.contribution(paper.doi)
        results[paper.doi] = res.data
      } catch {
        results[paper.doi] = { node_count: 0, root_concept: undefined }
      }
    }
  }
  setContributions(results)
}
```

- [ ] **Step 4: Update loadPapers to use folder filter**

```tsx
const loadPapers = () => {
  papersApi.list(undefined, activeFolder).then(res => {
    setPapers(res.data)
    setLoading(false)
    loadContributions(res.data)
  }).catch(err => {
    console.error('Failed to load papers:', err)
    setLoading(false)
  })
}
```

- [ ] **Step 5: Update useEffect**

```tsx
useEffect(() => {
  loadPapers()
  loadFolders()
}, [activeFolder])
```

- [ ] **Step 6: Add folder handlers**

```tsx
const handleCreateFolder = async (name: string, description: string) => {
  try {
    await foldersApi.create({ name, description })
    loadFolders()
    setShowCreateFolder(false)
  } catch {
    alert('创建失败')
  }
}

const handleDeleteFolder = async (folderId: string) => {
  if (!confirm('确定删除此文件夹？论文将移到默认文件夹。')) return
  try {
    await foldersApi.delete(folderId)
    if (activeFolder === folderId) setActiveFolder('default')
    loadFolders()
    loadPapers()
  } catch {
    alert('删除失败')
  }
}
```

- [ ] **Step 7: Replace the return JSX with new layout**

Replace the entire return statement with:

```tsx
return (
  <div className="flex h-[calc(100vh-80px)]">
    {/* Folder Sidebar */}
    <div className="w-64 bg-white border-r flex flex-col">
      <div className="p-4 border-b">
        <h2 className="font-semibold text-gray-700">文件夹</h2>
      </div>
      <div className="flex-1 overflow-y-auto">
        {folders.map(folder => (
          <button
            key={folder.id}
            onClick={() => setActiveFolder(folder.id)}
            className={`w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 ${
              activeFolder === folder.id ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-500' : 'text-gray-700'
            }`}
          >
            <div className="flex items-center gap-2">
              <Folder className="h-4 w-4" />
              <span className="text-sm">{folder.name}</span>
            </div>
            <span className="text-xs text-gray-400">{folder.paper_count}</span>
          </button>
        ))}
      </div>
      <div className="p-4 border-t">
        <button
          onClick={() => setShowCreateFolder(true)}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
        >
          <FolderPlus className="h-4 w-4" />
          新建文件夹
        </button>
      </div>
    </div>

    {/* Main Content */}
    <div className="flex-1 overflow-y-auto p-6">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold">论文管理</h1>
          <div className="flex gap-4">
            <button
              onClick={() => { loadPapers(); loadFolders(); }}
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

        {/* Upload Results - unchanged */}
        {uploadResults.length > 0 && (
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-medium mb-3">上传结果</h3>
            <div className="space-y-2">
              {uploadResults.map((result, idx) => (
                <div key={idx} className={`flex items-start p-2 rounded ${result.success ? 'bg-green-50' : 'bg-red-50'}`}>
                  {result.success ? (
                    <CheckCircle className="h-4 w-4 text-green-500 mr-2 mt-0.5" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-500 mr-2 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <div className="font-medium">{result.filename}</div>
                    {result.success && result.title && (
                      <div className="text-sm text-gray-500">{result.title}</div>
                    )}
                    {result.message && (
                      <div className={`text-sm ${result.status === 'processed' ? 'text-green-600' : result.status === 'pending' ? 'text-yellow-600' : 'text-gray-500'}`}>
                        {result.message}
                      </div>
                    )}
                    {!result.success && result.error && (
                      <div className="text-sm text-red-500">{result.error}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Batch Progress - unchanged */}
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

        {/* Paper Table */}
        {papers.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <FileText className="h-12 w-12 mx-auto text-gray-400" />
            <p className="mt-4 text-gray-500">暂无论文，上传 PDF 开始</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">标题</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">节点数</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">根概念</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {papers.map(paper => (
                  <tr key={paper.doi} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">{paper.title}</div>
                      {paper.authors && paper.authors.length > 0 && (
                        <div className="text-sm text-gray-500">
                          {Array.isArray(paper.authors) ? paper.authors.slice(0, 3).join(', ') : paper.authors}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs rounded-full ${getStatusBadge(paper.status)}`}>
                        {paper.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {paper.status === 'processed' ? (contributions[paper.doi]?.node_count || '-') : '-'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {paper.status === 'processed' ? (contributions[paper.doi]?.root_concept || '-') : '-'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        {paper.status === 'pending' && (
                          <button
                            onClick={() => handleProcess(paper.doi)}
                            disabled={processing === paper.doi}
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                            title="处理论文"
                          >
                            {processing === paper.doi ? (
                              <RefreshCw className="h-4 w-4 animate-spin" />
                            ) : (
                              <Play className="h-4 w-4" />
                            )}
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(paper.doi)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded"
                          title="删除"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>

    {/* Create Folder Modal */}
    {showCreateFolder && (
      <CreateFolderModal
        onClose={() => setShowCreateFolder(false)}
        onCreate={handleCreateFolder}
      />
    )}
  </div>
)
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/Papers.tsx
git commit -m "feat(frontend): add folder sidebar and contribution columns to Papers page"
```

---

## Task 12: Update ConceptsGraph.tsx with folder selector

**Files:**
- Modify: `frontend/src/pages/ConceptsGraph.tsx`

- [ ] **Step 1: Add imports and folder state**

Add to imports:

```tsx
import { foldersApi } from '../lib/api'
import { ChevronDown } from 'lucide-react'
```

Add state after existing state declarations:

```tsx
const [folders, setFolders] = useState<{id: string, name: string}[]>([])
const [activeFolder, setActiveFolder] = useState('default')
const [showFolderMenu, setShowFolderMenu] = useState(false)
```

- [ ] **Step 2: Add loadFolders and update useEffect**

```tsx
const loadFolders = () => {
  foldersApi.list().then(res => {
    setFolders(res.data)
  })
}

useEffect(() => {
  loadFolders()
  loadData()
}, [activeFolder])
```

- [ ] **Step 3: Update loadData to use folder filter**

Modify the loadData function to pass the folder parameter to the API calls (if the backend supports folder filtering for graph data).

- [ ] **Step 4: Add folder selector to header**

Find the header section and add folder selector:

```tsx
{/* Header with folder selector */}
<div className="flex justify-between items-center mb-4">
  <h1 className="text-2xl font-bold">概念图谱</h1>
  <div className="flex items-center gap-4">
    {/* Folder Selector */}
    <div className="relative">
      <button
        onClick={() => setShowFolderMenu(!showFolderMenu)}
        className="flex items-center gap-2 px-4 py-2 border rounded-lg hover:bg-gray-50"
      >
        <span>文件夹: {folders.find(f => f.id === activeFolder)?.name || '默认'}</span>
        <ChevronDown className="h-4 w-4" />
      </button>
      {showFolderMenu && (
        <div className="absolute right-0 mt-2 w-48 bg-white border rounded-lg shadow-lg z-10">
          {folders.map(folder => (
            <button
              key={folder.id}
              onClick={() => {
                setActiveFolder(folder.id)
                setShowFolderMenu(false)
              }}
              className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 ${
                activeFolder === folder.id ? 'bg-blue-50 text-blue-700' : ''
              }`}
            >
              {folder.name}
            </button>
          ))}
        </div>
      )}
    </div>

    {/* Existing buttons */}
    <button onClick={handleExport} ...>导出</button>
    <button onClick={() => setShowDedup(true)} ...>去重</button>
  </div>
</div>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ConceptsGraph.tsx
git commit -m "feat(frontend): add folder selector to ConceptsGraph page"
```

---

## Task 13: Final integration and testing

- [ ] **Step 1: Test the complete flow**

1. Start backend: `python -m uvicorn backend.main:app --reload --port 8088`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173

- [ ] **Step 2: Verify features**

1. **Concept Matching**: Upload a paper with known concepts, verify it matches existing tree
2. **Folder Creation**: Click "新建文件夹", create a folder
3. **Paper Assignment**: Upload paper to the new folder
4. **Contribution Display**: Verify node count and root concept show in table
5. **Folder Delete**: Delete folder, verify papers move to default
6. **Cascade Delete**: Delete paper, verify orphaned concepts are removed

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete concept extraction optimization and folder management"
```

---

## Summary

This plan implements:
1. **Concept Extraction Optimization**: Pass existing concept tree to LLM for smart matching
2. **Folder Management**: Create/delete folders, filter papers by folder
3. **Paper Contribution Display**: Show node count and root concept per paper
4. **Cascade Delete**: Remove orphaned concepts when deleting papers