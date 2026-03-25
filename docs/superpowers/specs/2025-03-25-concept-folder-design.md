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

**File: `frontend/src/pages/Papers.tsx`**

- Add folder sidebar on the left
- Show folder list with paper counts
- Click folder to filter papers
- Add "Create Folder" button
- Add "Delete Folder" action (with confirmation)

**File: `frontend/src/pages/Concepts.tsx`**

- Add folder selector in the header
- Filter concept tree by selected folder

**File: `frontend/src/lib/api.ts`**

Add `foldersApi`:
```typescript
export const foldersApi = {
  list: () => api.get<FolderListResponse>('/folders/'),
  create: (data: CreateFolderRequest) => api.post<FolderResponse>('/folders/', data),
  update: (id: string, data: UpdateFolderRequest) => api.patch<FolderResponse>(`/folders/${id}`, data),
  delete: (id: string) => api.delete(`/folders/${id}`),
}
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

- [ ] Add `get_concept_tree_summary()` to `openclaw/graph.py`
- [ ] Modify `_build_extraction_prompt()` to accept and include existing concepts
- [ ] Modify `process_paper()` to fetch and pass existing concepts
- [ ] Test with papers containing known concepts

### Phase 2: Folder Management

- [ ] Add `folders` table to database schema
- [ ] Add `folder_id` column to `papers` table
- [ ] Add folder CRUD methods to `database.py`
- [ ] Create `backend/routes/folders.py`
- [ ] Modify `papers.py` to support folder filtering
- [ ] Update frontend Papers.tsx with folder sidebar
- [ ] Update frontend Concepts.tsx with folder selector
- [ ] Add `foldersApi` to frontend

### Phase 3: Cascade Delete

- [ ] Add `delete_paper_cascade()` to `database.py`
- [ ] Modify `delete_paper()` in `papers.py`
- [ ] Test: delete paper, verify concepts are cleaned up

---

## Testing Plan

1. **Concept Matching**: Upload paper with "深度学习", verify it appears under "人工智能→机器学习"
2. **Folder Creation**: Create folder, verify it appears in list
3. **Paper Assignment**: Upload paper to folder, verify filter works
4. **Folder Delete**: Delete folder, verify papers move to default
5. **Cascade Delete**: Delete paper, verify orphaned concepts are removed