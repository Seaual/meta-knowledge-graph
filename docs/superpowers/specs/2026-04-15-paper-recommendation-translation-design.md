# 论文推荐自动翻译概念名 — 设计文档

> **问题：** 中文用户在概念页面或聊天页面请求论文推荐时，由于概念缺少 `text_en`（英文翻译），系统用中文概念名搜索 Semantic Scholar，返回空结果，导致前端面板加载后空白。

## 问题诊断

**根因：** 论文推荐在两个路径中都使用中文概念名搜索 S2：

### 路径 1：概念页面推荐面板

- **入口：** `RecommendationPanel.tsx` → `recommendationApi.searchPapersByConcept()`
- **后端路由：** `backend/routes/concepts_research.py:15` → `research_service.search_papers_by_concept()`
- **问题代码：** `research_service.py:181` — `query = concept.get("text_en") or concept["text"]`
- **结果：** 当 `text_en` 为空时，用中文名搜索 S2，返回空列表 → 前端 `papers` 数组为空 → 面板加载后空白

### 路径 2：聊天页面 Agent 推荐

- **入口：** 用户在聊天中请求"推荐相关论文"
- **Agent 工具：** `mkg/agent/tools.py:482` → `recommend_papers()`
- **问题代码：** `tools.py:506-511` — 查找到概念后，优先用 `text_en`，但为空时回退到中文 `text`
- **结果：** 同样用中文名搜索 S2，返回空结果

## 解决方案

**核心思路：** 在两个论文推荐路径中，如果概念缺少 `text_en`，自动调用已有的 LLM 翻译服务翻译概念名并保存到数据库，然后用英文搜索 S2。

**复用已有服务：** `backend/services/concept_translation.py` 中的 `translate_concept_if_needed()` 函数已实现：
1. 检查概念是否有 `text_en`
2. 如果没有，调用 LLM 翻译
3. 翻译结果保存到数据库
4. 翻译失败时降级返回中文名

## 架构变更

### 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/services/research_service.py` | 修改 | `search_papers_by_concept` 方法中触发翻译 |
| `mkg/agent/tools.py` | 修改 | `recommend_papers` 函数中触发翻译 |

### 不需要新建

- `backend/services/concept_translation.py` — 已存在，直接复用
- `mkg/database.py` — `get_concept_by_text` 已在 i18n 任务中支持英文搜索

## 修改详情

### 修改 1：`research_service.py`

**位置：** `search_papers_by_concept()` 方法，第 170-181 行

**当前逻辑：**
```python
concept = self.db.concepts.get(concept_id)
if not concept:
    return {"error": "Concept not found", "concept_id": concept_id}

if not self.s2_client:
    return {"error": "S2 client not configured", "concept_id": concept_id}

try:
    query = concept.get("text_en") or concept["text"]
    papers = self.s2_client.search_papers(query, limit=limit * 2)
```

**修改后逻辑：**
```python
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
```

### 修改 2：`tools.py`

**位置：** `recommend_papers()` 函数，第 498-516 行

**当前逻辑：**
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

**修改后逻辑：**
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

## 执行流程

```
用户请求论文推荐（概念页面 或 聊天页面）
  ↓
获取概念对象
  ↓
检查 text_en 是否存在？
  ├─ 存在 → 直接使用 text_en 搜索 S2
  └─ 不存在
       ↓
  translate_concept_if_needed()
       ↓
  LLM 翻译中文概念名 → 英文
       ↓
  保存到数据库 (UPDATE concepts SET text_en = ?)
       ↓
  重新获取概念 → 使用 text_en 搜索 S2
  ↓
返回论文列表 → 前端展示
```

## 边界情况处理

1. **LLM 翻译失败** — `translate_concept_if_needed` 内部已处理异常，失败时返回中文名，搜索仍会执行但可能无结果
2. **概念不存在** — 两个路径都已处理概念不存在的情况，返回错误信息
3. **S2 客户端未配置** — 已处理，返回错误信息
4. **重复翻译** — `translate_concept_if_needed` 只在 `text_en` 为空时触发，已翻译的概念不会重复翻译
5. **翻译速度慢** — LLM 翻译是同步操作，会增加请求响应时间（通常 1-3 秒），但翻译结果会保存到数据库，后续搜索不再需要翻译

## 性能考量

- **首次搜索：** 需要 LLM 翻译（~1-3秒）+ S2 搜索（~1-2秒） = ~2-5秒
- **后续搜索：** 直接使用已保存的 `text_en`，只需 S2 搜索（~1-2秒）
- **历史概念翻译：** 所有缺少 `text_en` 的历史概念会在第一次论文推荐请求时自动翻译并缓存

## 不需要前端变更

前端代码不需要修改，因为：
1. API 响应格式不变（仍然是 `{papers: [...], total: N}`）
2. 前端只是接收和展示论文列表
3. 翻译逻辑完全在后端透明执行
