# 论文推荐自动翻译概念名 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在两个论文推荐路径（概念页面推荐、聊天页面 Agent 推荐）中，自动翻译缺少 `text_en` 的中文概念名，确保 S2 搜索始终使用英文，返回有效的论文结果。

**Architecture:** 复用已有的 `concept_translation.py` 中的 `translate_concept_if_needed()` 函数，在 `research_service.search_papers_by_concept()` 和 `tools.recommend_papers()` 中，获取概念后检查 `text_en`，若为空则触发翻译并保存，然后用英文名搜索 S2。

**Tech Stack:** FastAPI + Python (后端), SQLite (数据库), LangChain LLM (翻译)

---

### Task 1: research_service.py — 概念页面推荐自动翻译

**Files:**
- Modify: `backend/services/research_service.py:168-199`

- [ ] **Step 1: 修改 `search_papers_by_concept` 方法**

将 `search_papers_by_concept` 方法从当前实现替换为以下代码。修改核心：在 S2 搜索前，如果概念缺少 `text_en`，调用 `translate_concept_if_needed` 翻译并重新获取概念。

```python
def search_papers_by_concept(self, concept_id: str, year: str = None,
                              min_citations: int = None, limit: int = 10) -> dict:
    """搜索概念相关论文"""
    concept = self.db.concepts.get(concept_id)
    if not concept:
        return {"error": "Concept not found", "concept_id": concept_id}

    if not self.s2_client:
        return {"error": "S2 client not configured", "concept_id": concept_id}

    # 如果概念缺少英文名，自动翻译
    if not concept.get("text_en"):
        from backend.services.concept_translation import translate_concept_if_needed
        translate_concept_if_needed(concept, self.db)
        concept = self.db.concepts.get(concept_id)  # 重新获取更新后的概念

    try:
        # 始终使用英文概念名搜索 Semantic Scholar
        query = concept.get("text_en") or concept["text"]
        papers = self.s2_client.search_papers(query, limit=limit * 2)

        # 过滤
        if year:
            papers = [p for p in papers if str(p.get("year")) == year]
        if min_citations:
            papers = [p for p in papers if p.get("citationCount", 0) >= min_citations]

        papers = papers[:limit]

        return {
            "concept_id": concept_id,
            "concept_text": concept.get("text_en") or concept["text"],
            "papers": papers,
            "total": len(papers)
        }
    except Exception as e:
        return {"error": str(e), "concept_id": concept_id}
```

关键变更：
1. 添加了 `if not concept.get("text_en"):` 检查块，触发翻译
2. 翻译后 `concept = self.db.concepts.get(concept_id)` 重新获取更新后的概念
3. `concept_text` 返回优先使用 `text_en`（`concept.get("text_en") or concept["text"]`）

- [ ] **Step 2: 验证语法**

Run: `cd D:\meta-knowledge-graph-main && python -c "import ast; ast.parse(open('backend/services/research_service.py').read())"`
Expected: No output (syntax valid)

- [ ] **Step 3: Commit**

```bash
git add backend/services/research_service.py
git commit -m "feat: auto-translate concept names before S2 search in paper recommendation"
```

---

### Task 2: tools.py — 聊天页面 Agent 推荐自动翻译

**Files:**
- Modify: `mkg/agent/tools.py:482-543`

- [ ] **Step 1: 修改 `recommend_papers` 函数**

将概念查找和搜索 query 构建部分（第 497-516 行）替换为以下代码。在查找到概念后、搜索前，如果概念缺少 `text_en`，触发翻译。

将第 497-516 行：

```python
    # 查找概念（获取英文名用于搜索）
    concept = _db.get_concept_by_text(concept_name)
    if not concept:
        all_concepts = _db.get_all_concepts()
        for c in all_concepts:
            if concept_name.lower() in (c.get('text') or '').lower():
                concept = c
                break

    # 使用英文名搜索（如果有），否则用中文名
    search_query = concept_name
    if concept and concept.get('text_en'):
        search_query = concept['text_en']
    elif concept:
        search_query = concept.get('text', concept_name)

    papers = []
    if _s2_client:
        try:
            results = _s2_client.search_papers(search_query, limit=limit)
```

替换为：

```python
    # 查找概念
    concept = _db.get_concept_by_text(concept_name)
    if not concept:
        all_concepts = _db.get_all_concepts()
        for c in all_concepts:
            if concept_name.lower() in (c.get('text') or '').lower():
                concept = c
                break

    # 如果概念缺少英文名，自动翻译
    if concept and not concept.get('text_en'):
        from backend.services.concept_translation import translate_concept_if_needed
        translate_concept_if_needed(concept, _db)
        concept = _db.get_concept(concept['id'])  # 重新获取更新后的概念

    # 始终优先使用英文概念名搜索
    search_query = concept.get('text_en') if concept else concept_name

    papers = []
    if _s2_client:
        try:
            results = _s2_client.search_papers(search_query, limit=limit)
```

关键变更：
1. 添加了 `if concept and not concept.get('text_en'):` 检查块
2. 翻译后 `concept = _db.get_concept(concept['id'])` 重新获取（注意 `_db` 是 `Database` 实例，`get_concept` 方法存在）
3. `search_query` 简化为 `concept.get('text_en') if concept else concept_name`，始终优先使用英文

- [ ] **Step 2: 验证语法**

Run: `cd D:\meta-knowledge-graph-main && python -c "import ast; ast.parse(open('mkg/agent/tools.py').read())"`
Expected: No output (syntax valid)

- [ ] **Step 3: Commit**

```bash
git add mkg/agent/tools.py
git commit -m "feat: auto-translate concept names before S2 search in agent recommend_papers tool"
```

---

### Task 3: 端到端验证

- [ ] **Step 1: 重启后端**

Run: `cd D:\meta-knowledge-graph-main && venv/Scripts/activate && python -m uvicorn backend.main:app --reload --port 8089`
Expected: Backend starts on port 8089

- [ ] **Step 2: 概念页面推荐测试**

1. 打开浏览器，进入概念页面
2. 选择一个缺少 `text_en` 的中文概念
3. 点击论文推荐按钮
4. 观察：面板应显示加载动画，随后显示论文列表（不再空白）
5. 检查数据库：该概念的 `text_en` 字段应已被填充

- [ ] **Step 3: 聊天页面推荐测试**

1. 在聊天中输入："推荐相关论文"（针对一个中文概念）
2. 观察：Agent 应调用 `recommend_papers` 工具，返回英文论文列表
3. 检查响应中论文数量 > 0

- [ ] **Step 4: 已有英文概念测试**

1. 选择一个已有 `text_en` 的概念
2. 触发论文推荐
3. 观察：不应触发翻译，直接使用已有的英文名搜索，速度更快

- [ ] **Step 5: Commit（如有修复）**

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/services/research_service.py` | 修改 | `search_papers_by_concept` 添加翻译触发逻辑 |
| `mkg/agent/tools.py` | 修改 | `recommend_papers` 添加翻译触发逻辑 |
