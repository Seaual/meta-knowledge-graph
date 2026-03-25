# Concept Extraction and Folder Management Design Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optimize concept extraction to properly match existing concepts, add folder management for papers, and clean up orphaned nodes when deleting papers.

**Architecture:** Prompt enhancement with existing concept context → Database schema for folders → API endpoints for folder CRUD → Frontend folder navigation → Cascade delete for paper removal.

---

## Feature A: Concept Extraction Optimization

### Problem

When extracting concepts from a new paper, the system doesn't reference existing concepts in the database. This causes:
1. Duplicate concepts with wrong parent relationships (e.g., "深度学习" appears under "统筹学" instead of "人工智能→机器学习")
2. Root concept count doesn't change because new concepts become orphaned nodes

### Solution

Pass existing concept tree to LLM as context before extraction. LLM will intelligently place new concepts in the correct position.

### Changes

**File: `openclaw/pdf_parser.py`**

Modify `_build_extraction_prompt()` to:
1. Accept a new parameter `existing_concepts: dict`
2. Add a section "已有概念树（参考）" in the prompt
3. Include simplified concept tree (concept names and hierarchy only)

**File: `openclaw/graph.py`**

Add method `get_concept_tree_summary()` to return a simplified tree structure for prompt context.

**File: `backend/routes/papers.py`**

Modify `process_paper()` to:
1. Fetch existing concept tree before calling `get_extractor()`
2. Pass it to the extraction prompt

### Prompt Addition

```
## 已有概念树（参考）

当前知识图谱中已有以下概念结构，新概念请尽量归类到合适的位置：

{existing_tree}

**重要规则：**
1. 如果新提取的概念已存在于上述树中，请使用相同的概念名和正确的父节点路径
2. 如果新概念是已有概念的子概念，请放在正确位置
3. 只有当概念确实是新的研究领域时，才创建新的根概念
```

---

## Feature B: Folder Management

### Database Schema

**New table: `folders`**

```sql
CREATE TABLE IF NOT EXISTS folders (
    id TEXT PRIMARY KEY,           -- slug: "default", "reinforcement-learning"
    name TEXT NOT NULL,            -- 显示名: "默认", "强化学习论文集"
    description TEXT,
    paper_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Modify table: `papers`**

```sql
ALTER TABLE papers ADD COLUMN folder_id TEXT DEFAULT 'default';
```

**Default folder**: Insert "default" folder on first run.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/folders` | GET | List all folders with paper counts |
| `/api/folders` | POST | Create new folder |
| `/api/folders/{id}` | PATCH | Update folder name/description |
| `/api/folders/{id}` | DELETE | Delete folder, move papers to default |
| `/api/papers?folder={id}` | GET | List papers in folder |
| `/api/papers/{doi}/folder` | PATCH | Move paper to different folder |

### Backend Changes

**File: `openclaw/database.py`**

Add methods:
- `get_all_folders()` - Get folders with paper counts
- `create_folder(folder_data)` - Create new folder
- `update_folder(folder_id, data)` - Update folder
- `delete_folder(folder_id)` - Delete folder, reassign papers to default
- `move_paper_to_folder(doi, folder_id)` - Move paper
- `get_papers_by_folder(folder_id)` - Get papers in folder

**File: `backend/routes/folders.py`** (new)

Create folder management routes.

**File: `backend/routes/papers.py`**

Modify:
- `list_papers()` - Add folder filter
- `upload_paper()` - Accept folder_id parameter
- Add `move_paper()` endpoint

### Frontend Changes

#### File: `frontend/src/pages/Papers.tsx` - UI Layout Change

**Current layout**: Single column with table
**New layout**: Two columns - folder sidebar on left, paper table on right

```
┌─────────────────────────────────────────────────────────────┐
│ 论文管理                    [刷新] [批量处理] [上传PDF]      │
├──────────────┬──────────────────────────────────────────────┤
│              │                                               │
│  📁 默认 (5) │  标题           状态    节点数  根概念  操作  │
│  📁 强化学习  │  ─────────────────────────────────────────── │
│  📁 NLP论文  │  Paper 1        pending   -       -    [处理]│
│              │  Paper 2        processed  12   深度学习  [删除]│
│  [+ 新建文件夹]│  Paper 3        processed  8    机器学习  [删除]│
│              │                                               │
└──────────────┴──────────────────────────────────────────────┘
```

**Changes:**
1. Add folder sidebar (w-64) on the left
2. Show folder list with paper counts
3. Active folder highlighted
4. "Create Folder" button at bottom of sidebar
5. Folder right-click menu: Rename, Delete
6. Paper table adds two columns:
   - **节点数**: Number of concepts contributed by this paper
   - **根概念**: The root concept name this paper's concepts belong to

#### File: `frontend/src/pages/ConceptsGraph.tsx` - Folder Selector

**Add folder selector in header:**

```
┌─────────────────────────────────────────────────────────────┐
│ 概念图谱              [文件夹: 默认 ▼]      [导出] [去重]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    [Force Graph Canvas]                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Changes:**
1. Add folder dropdown selector in header
2. Graph filters to show only concepts from papers in selected folder
3. Default folder is "默认"

#### File: `frontend/src/components/CreateFolderModal.tsx` (new)

Simple modal for creating new folder:
- Folder name input
- Description input (optional)
- Cancel / Create buttons

#### File: `frontend/src/lib/api.ts`

Add `foldersApi`:
```typescript
export const foldersApi = {
  list: () => api.get<FolderListResponse>('/folders/'),
  create: (data: CreateFolderRequest) => api.post<FolderResponse>('/folders/', data),
  update: (id: string, data: UpdateFolderRequest) => api.patch<FolderResponse>(`/folders/${id}`, data),
  delete: (id: string) => api.delete(`/folders/${id}`),
}
```

Modify `papersApi`:
```typescript
list: (status?: string, folder?: string) => api.get('/papers/', { params: { status, folder } }),
upload: (file: File, folder?: string) => { ... },  // Add folder parameter
moveToFolder: (doi: string, folderId: string) => api.patch(`/papers/${doi}/folder`, { folder_id: folderId }),
```

---

## Feature C: Cascade Delete for Papers

### Problem

When deleting a paper, its associated concepts remain in the database, creating orphaned nodes.

### Solution

When deleting a paper, check each associated concept:
1. If no other papers reference the concept, delete it
2. Recursively check and delete child concepts if they become orphaned
3. Clean up concept_relations records

### Implementation

**File: `openclaw/database.py`**

Add method:
```python
def delete_paper_cascade(self, doi: str):
    """Delete paper and orphaned concepts"""
    # 1. Get all concepts associated with this paper
    # 2. Delete paper_concepts records
    # 3. For each concept, check if other papers reference it
    # 4. If not, delete concept and check children recursively
    # 5. Clean up concept_relations
```

**File: `backend/routes/papers.py`**

Modify `delete_paper()` to call `delete_paper_cascade()` instead of manual cleanup.

---

## Implementation Tasks

### Phase 1: Concept Extraction Optimization

- [ ] Add `get_concept_tree_summary()` to `openclaw/graph.py` - return simplified tree for prompt context
- [ ] Modify `_build_extraction_prompt()` in `openclaw/pdf_parser.py` to accept and include existing concepts
- [ ] Modify `process_paper()` in `backend/routes/papers.py` to fetch and pass existing concepts
- [ ] Test with papers containing known concepts

### Phase 2: Folder Management - Backend

- [ ] Add `folders` table to `openclaw/database.py` schema
- [ ] Add `folder_id` column to `papers` table (default 'default')
- [ ] Insert default folder on first run
- [ ] Add folder CRUD methods to `database.py`: `get_all_folders()`, `create_folder()`, `update_folder()`, `delete_folder()`
- [ ] Add paper-folder methods: `get_papers_by_folder()`, `move_paper_to_folder()`
- [ ] Create `backend/routes/folders.py` with folder endpoints
- [ ] Modify `backend/routes/papers.py` to support folder filter and upload with folder
- [ ] Add `get_paper_contribution()` method to return node count and root concept for a paper

### Phase 3: Folder Management - Frontend

- [ ] Add `foldersApi` and update `papersApi` in `frontend/src/lib/api.ts`
- [ ] Create `frontend/src/components/CreateFolderModal.tsx`
- [ ] Modify `frontend/src/pages/Papers.tsx`:
  - Add folder sidebar (left side, w-64)
  - Show folder list with paper counts
  - Click folder to filter papers
  - Add "Create Folder" button
  - Right-click folder for rename/delete
  - Add "节点数" and "根概念" columns to paper table
- [ ] Modify `frontend/src/pages/ConceptsGraph.tsx`:
  - Add folder dropdown selector in header
  - Filter graph by selected folder

### Phase 4: Cascade Delete

- [ ] Add `delete_paper_cascade()` to `openclaw/database.py`
- [ ] Modify `delete_paper()` in `backend/routes/papers.py` to use cascade delete
- [ ] Test: delete paper, verify orphaned concepts are removed

---

## Testing Plan

1. **Concept Matching**: Upload paper with "深度学习", verify it appears under "人工智能→机器学习"
2. **Folder Creation**: Create folder, verify it appears in sidebar
3. **Paper Assignment**: Upload paper to folder, verify filter works
4. **Paper Contribution**: Verify node count and root concept show in paper table
5. **Folder Delete**: Delete folder, verify papers move to default
6. **Cascade Delete**: Delete paper, verify orphaned concepts are removed