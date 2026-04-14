# 多语言 i18n 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的中/英文双语支持 — 前端 UI 跟随用户语言偏好，搜索始终使用英文，概念名双语展示，其他内容保持原始语言。

**Architecture:** 前端通过 `Accept-Language` 请求头传播语言偏好，后端通过 ContextVar 在请求级别读取语言，概念本地化和搜索逻辑据此适配。搜索层强制使用 `text_en`，研究点 prompt 优先使用英文概念名。概念缺少 `text_en` 时按需调用 LLM 翻译补全。

**Tech Stack:** React + TypeScript (前端), FastAPI + Python (后端), SQLite + Neo4j (数据库)

---

### Task 1: 前端 i18n 导出 getLanguage() 函数

**Files:**
- Modify: `frontend/src/i18n/index.tsx`

- [ ] **Step 1: 添加 getLanguage() 导出**

在 `frontend/src/i18n/index.tsx` 末尾添加：

```typescript
const LANGUAGE_KEY = "mkg_language";

export function getLanguage(): string {
  return typeof window !== "undefined"
    ? (localStorage.getItem(LANGUAGE_KEY) || "zh")
    : "zh";
}
```

注意：文件中已有 `LANGUAGE_KEY` 定义（第18行），不要重复定义，直接复用现有的。

- [ ] **Step 2: 验证编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors related to i18n

- [ ] **Step 3: Commit**

```bash
git add frontend/src/i18n/index.tsx
git commit -m "feat: export getLanguage() for API client interceptor"
```

---

### Task 2: 前端 API Client 添加 Accept-Language 拦截器

**Files:**
- Modify: `frontend/src/lib/api/client.ts`

- [ ] **Step 1: 添加 Accept-Language 拦截器**

在现有的 `X-Device-ID` interceptor 之后，添加语言头拦截器：

```typescript
import { getLanguage } from '../../i18n';

// Add Accept-Language header to all requests
api.interceptors.request.use((config) => {
  config.headers['Accept-Language'] = getLanguage();
  return config;
});
```

完整文件最终内容：

```typescript
import axios from "axios";
import { getLanguage } from '../../i18n';

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

// Device ID management
const DEVICE_ID_KEY = "mkg_device_id";

function getOrCreateDeviceId(): string {
  let deviceId = localStorage.getItem(DEVICE_ID_KEY);
  if (!deviceId) {
    deviceId = crypto.randomUUID();
    localStorage.setItem(DEVICE_ID_KEY, deviceId);
  }
  return deviceId;
}

// Add device ID header to all requests
api.interceptors.request.use((config) => {
  const deviceId = getOrCreateDeviceId();
  config.headers["X-Device-ID"] = deviceId;
  return config;
});

// Add Accept-Language header to all requests
api.interceptors.request.use((config) => {
  config.headers["Accept-Language"] = getLanguage();
  return config;
});

export default api;
export { getOrCreateDeviceId };
```

- [ ] **Step 2: 验证编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api/client.ts
git commit -m "feat: add Accept-Language interceptor to API client"
```

---

### Task 3: 后端语言中间件和本地化工具

**Files:**
- Modify: `backend/dependencies.py`
- Modify: `backend/main.py`
- Create: `backend/services/localization.py`
- Create: `backend/services/concept_translation.py`

- [ ] **Step 1: 创建 localization.py**

```python
# backend/services/localization.py
"""概念本地化工具 — 根据用户语言返回对应的概念名"""


def localize_concept(concept: dict, lang: str) -> dict:
    """根据语言返回对应的概念名"""
    if not concept:
        return concept
    if lang == "en" and concept.get("text_en"):
        return {**concept, "text": concept["text_en"]}
    return concept


def localize_concept_list(concepts: list[dict], lang: str) -> list[dict]:
    """批量本地化概念列表"""
    return [localize_concept(c, lang) for c in concepts]
```

- [ ] **Step 2: 创建 concept_translation.py**

```python
# backend/services/concept_translation.py
"""概念翻译服务 — 当概念缺少 text_en 时自动翻译补全"""

import logging

from mkg.database import Database
from mkg.llm import get_llm_or_raise

logger = logging.getLogger(__name__)


def translate_concept_if_needed(concept: dict, db: Database) -> str:
    """如果概念缺少英文名，自动翻译并保存"""
    if concept.get("text_en"):
        return concept["text_en"]

    try:
        llm = get_llm_or_raise()
        prompt = f"将以下中文学术概念翻译为英文，只返回翻译结果，不要其他内容：{concept['text']}"
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        if isinstance(content, list):
            content = '\n'.join(
                item.get('text', str(item)) if isinstance(item, dict) else str(item)
                for item in content
            )
        en_name = content.strip()

        # 保存到数据库
        cursor = db.conn.cursor()
        cursor.execute(
            "UPDATE concepts SET text_en = ? WHERE id = ?",
            (en_name, concept["id"])
        )
        db.conn.commit()

        return en_name
    except Exception as e:
        logger.warning(f"Failed to translate concept '{concept.get('text', '')}': {e}")
        return concept.get("text", "")
```

- [ ] **Step 3: 修改 dependencies.py 添加语言 ContextVar**

读取 `backend/dependencies.py` 现有内容，在文件末尾添加：

```python
from contextvars import ContextVar

_request_language: ContextVar[str] = ContextVar("language", default="zh")


def get_language() -> str:
    """获取当前请求的用户语言偏好"""
    return _request_language.get()


def set_language(lang: str):
    """设置当前请求的语言（由 middleware 调用）"""
    _request_language.set(lang)
```

- [ ] **Step 4: 修改 main.py 注册语言中间件**

在 `backend/main.py` 中，在 CORS middleware 注册之后、routers 注册之前，添加：

```python
from backend.dependencies import set_language

@app.middleware("http")
async def language_middleware(request, call_next):
    lang = request.headers.get("Accept-Language", "zh")[:2]
    if lang not in ("zh", "en"):
        lang = "zh"
    set_language(lang)
    response = await call_next(request)
    return response
```

- [ ] **Step 5: Commit**

```bash
git add backend/services/localization.py backend/services/concept_translation.py backend/dependencies.py backend/main.py
git commit -m "feat: add language middleware and concept localization tools"
```

---

### Task 4: database.py get_concept_by_text 支持英文搜索

**Files:**
- Modify: `mkg/database.py:1101-1108`

- [ ] **Step 1: 修改 get_concept_by_text 同时搜索 text 和 text_en**

将 `mkg/database.py` 中的 `get_concept_by_text` 方法从：

```python
def get_concept_by_text(self, text: str) -> dict | None:
    """通过文本获取概念"""
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM concepts WHERE LOWER(text) = LOWER(?)", (text,))
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None
```

改为：

```python
def get_concept_by_text(self, text: str) -> dict | None:
    """通过文本（中/英文）获取概念"""
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM concepts WHERE LOWER(text) = LOWER(?)", (text,))
    row = cursor.fetchone()
    if row:
        return dict(row)
    cursor.execute("SELECT * FROM concepts WHERE LOWER(text_en) = LOWER(?)", (text,))
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None
```

- [ ] **Step 2: Commit**

```bash
git add mkg/database.py
git commit -m "fix: get_concept_by_text searches both text and text_en columns"
```

---

### Task 5: research_service.py 搜索始终使用英文

**Files:**
- Modify: `backend/services/research_service.py`

- [ ] **Step 1: 修改 search_papers_by_concept 使用 text_en**

将第 179 行的 `query = concept["text"]` 改为：

```python
# 始终使用英文概念名搜索 Semantic Scholar
query = concept.get("text_en") or concept["text"]
```

- [ ] **Step 2: 修改 _build_research_prompt 使用英文概念名**

在 `_build_research_prompt` 方法开头添加辅助函数：

```python
def _localized_name(c):
    """优先使用英文概念名"""
    return c.get("text_en") or c.get("text", "")
```

然后修改 prompt 中所有使用 `concept['text']` 和概念列表的地方：

- `{concept['text']}` → `{_localized_name(concept)}`
- ancestors 列表：`a.get('text', a.get('name', ''))` → `_localized_name(a)`
- descendants 列表：`d.get('text', d.get('name', ''))` → `_localized_name(d)`
- siblings 列表：`s.get('text', s.get('name', ''))` → `_localized_name(s)`
- edge_nodes 列表：`e.get('text', e.get('name', ''))` → `_localized_name(e)`

完整修改后的 `_build_research_prompt` 的 context 部分：

```python
def _build_research_prompt(
    self,
    concept: dict,
    ancestors: list,
    descendants: list,
    siblings: list,
    edge_nodes: list,
    papers: list,
) -> str:
    """构建研究点发现提示词 — 四种方法论"""

    def _localized_name(c):
        return c.get("text_en") or c.get("text", "")

    return f"""<s>
你是一位拥有 20 年经验的科研导师，擅长从知识图谱的结构特征中识别研究机会。

你发现研究点的四种方法论：
- **空白地带法**：图谱中两个本应有联系的分支之间缺少连接 → 未被探索的交叉方向
- **末端延伸法**：叶子节点代表最具体的技术 → 它们能否应用到其他分支？
- **瓶颈识别法**：某节点连接大量子节点但自身缺少兄弟节点 → 可能是领域瓶颈
- **迁移应用法**：一个分支的成熟方法 → 能否迁移到另一个问题尚未解决的分支？
</s>

<task>
基于以下知识图谱结构信息，发现 3-5 个有价值的潜在研究方向。
优先寻找**跨分支的交叉创新点**，而非已有方向的简单延伸。
</task>

<context>
## 焦点概念
- 名称：{_localized_name(concept)}
- 层级：{concept.get('category', 'unknown')}
- 关联论文数：{concept.get('paper_count', 0)}

## 上游路径（从根到当前概念的祖先链 — 学科脉络）
{json.dumps([{'text': _localized_name(a), 'category': a.get('category')} for a in ancestors], ensure_ascii=False, indent=2)}

## 下游分支（当前概念的后代 — 已有的研究细分）
{json.dumps([{'text': _localized_name(d), 'category': d.get('category'), 'paper_count': d.get('paper_count', 0)} for d in descendants], ensure_ascii=False, indent=2)}

## 邻域节点（共享父节点的不同分支 — 平行研究方向）
{json.dumps([{'text': _localized_name(s), 'category': s.get('category'), 'paper_count': s.get('paper_count', 0)} for s in siblings], ensure_ascii=False, indent=2)}

## 远端节点（图谱中距离较远的叶子 — 潜在跨领域连接机会）
{json.dumps([{'text': _localized_name(e), 'category': e.get('category')} for e in edge_nodes], ensure_ascii=False, indent=2)}

## 相关论文
{json.dumps([{'title': p.get('title', ''), 'research_questions': p.get('keywords', [])} for p in papers], ensure_ascii=False, indent=2)}
</context>

<output_format>
输出 JSON 数组，每个研究点包含：

[
  {{
    "title": "研究点标题（15字以内）",
    "hypothesis": "核心假设（用'如果将 X 应用于 Y，可能解决 Z 问题'的句式）",
    "description": "详细描述（80-150字），含问题背景、方法思路、预期结果",
    "discovery_method": "gap_filling | leaf_extension | bottleneck | transfer",
    "rationale": "为什么图谱结构暗示了这个研究机会（引用具体节点关系）",
    "related_concepts": ["涉及的概念名称"],
    "difficulty": "low | medium | high",
    "difficulty_reason": "难度依据（一句话）",
    "novelty": "incremental | moderate | high",
    "potential_impact": "niche | broad | transformative"
  }}
]

评分标准：

difficulty:
- low：现有方法直接扩展，3-6 个月
- medium：需新方法或新数据，6-12 个月
- high：基础理论创新或大规模实验，1 年以上

novelty:
- incremental：已有方法的小幅改进
- moderate：已有方法创造性应用于新问题
- high：新的问题定义或理论框架

potential_impact:
- niche：特定子领域的小范围影响
- broad：对整个研究方向有推动
- transformative：可能改变领域基本范式
</output_format>

只输出 JSON 数组，不要其他内容。
"""
```

- [ ] **Step 3: 修改 discover_research_points 返回的概念名**

将第 153 行的 `"concept_name": concept["text"]` 改为：

```python
"concept_name": concept.get("text_en") or concept["text"],
```

- [ ] **Step 4: Commit**

```bash
git add backend/services/research_service.py
git commit -m "fix: research service always uses English for S2 search and prompts"
```

---

### Task 6: mkg/agent/tools.py 搜索使用 text_en

**Files:**
- Modify: `mkg/agent/tools.py`

- [ ] **Step 1: 搜索概念时使用 text_en**

读取 `mkg/agent/tools.py` 中所有调用 `s2_client.search_papers` 和 `get_concept_by_text` 的地方。

对于搜索论文的 tool，确保使用 `text_en`：

```python
# 在 search_paper tool 中，如果传入概念名，优先用英文名
def search_paper(query: str):
    """Search for papers on Semantic Scholar"""
    papers = s2_client.search_papers(query, limit=10)
    ...
```

对于 `get_concept_graph` 和 `analyze_research_points` 中获取概念后进行搜索的场景，确保使用 `concept.get("text_en") or concept["text"]` 作为搜索 query。

具体修改位置取决于 tools.py 的当前实现，核心原则是：所有调用 `s2_client.search_papers()` 的 query 参数，如果来自概念名，必须使用 `text_en`。

- [ ] **Step 2: Commit**

```bash
git add mkg/agent/tools.py
git commit -m "fix: agent tools use text_en for Semantic Scholar searches"
```

---

### Task 7: 前端组件概念名语言感知

**Files:**
- Modify: `frontend/src/components/ConceptGraphInChat.tsx`
- Modify: `frontend/src/components/MiniConceptGraph.tsx`
- Modify: `frontend/src/components/cards/ResearchPointsCard.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`（如显示概念名）

- [ ] **Step 1: 添加 getConceptDisplayName 工具函数**

在 `frontend/src/lib/api/client.ts` 或新建 `frontend/src/lib/concept.ts`：

```typescript
import { getLanguage } from '../i18n';

export interface Concept {
  id: string;
  text: string;
  text_en?: string;
  text_zh?: string;
  concept?: string;
  category?: string;
  paper_count?: number;
  [key: string]: unknown;
}

export function getConceptDisplayName(concept: Concept): string {
  const lang = getLanguage();
  if (lang === 'en' && concept.text_en) {
    return concept.text_en;
  }
  return concept.concept || concept.text || 'Unnamed Concept';
}
```

- [ ] **Step 2: 修改 ConceptGraphInChat.tsx**

找到所有显示概念名的地方，将 `concept.concept` 或 `concept.text` 替换为 `getConceptDisplayName(concept)`。

- [ ] **Step 3: 修改 MiniConceptGraph.tsx**

同上，将概念名显示改为 `getConceptDisplayName(concept)`。

- [ ] **Step 4: 修改 ResearchPointsCard.tsx**

研究点数据中的 `related_concepts` 数组是字符串数组（概念名），这些来自后端 LLM 生成。由于 Task 5 已确保 LLM prompt 使用英文概念名，这些字符串已经是英文的，不需要额外处理。

但如果有直接从数据库获取的概念对象，也要用 `getConceptDisplayName`。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ConceptGraphInChat.tsx frontend/src/components/MiniConceptGraph.tsx frontend/src/components/cards/ResearchPointsCard.tsx frontend/src/lib/concept.ts
git commit -m "feat: concept names follow user language preference in UI components"
```

---

### Task 8: 后端概念 API 响应本地化

**Files:**
- Modify: `backend/routes/concepts.py`
- Modify: `backend/routes/concepts_tree.py`

- [ ] **Step 1: 修改 concepts.py 返回本地化概念**

在文件头部导入：

```python
from backend.dependencies import get_language
from backend.services.localization import localize_concept, localize_concept_list
```

在所有返回概念数据的端点中，添加语言参数并本地化：

```python
@router.get("/{concept_id}")
def get_concept(concept_id: str):
    lang = get_language()
    concept = db.concepts.get(concept_id)
    return localize_concept(concept, lang)
```

对于列表端点：

```python
@router.get("/")
def list_concepts():
    lang = get_language()
    concepts = db.concepts.get_all()
    return localize_concept_list(concepts, lang)
```

对于搜索端点：

```python
@router.get("/search")
def search_concepts(q: str):
    lang = get_language()
    # ... 搜索逻辑
    return localize_concept_list(results, lang)
```

- [ ] **Step 2: 修改 concepts_tree.py**

同上，在返回概念树/根概念的端点中添加本地化。

- [ ] **Step 3: Commit**

```bash
git add backend/routes/concepts.py backend/routes/concepts_tree.py
git commit -m "feat: concept API responses localized based on Accept-Language"
```

---

### Task 9: 概念 API 端点按需翻译补全

**Files:**
- Modify: `backend/routes/concepts.py`（或相关文件）

- [ ] **Step 1: 在概念获取时触发按需翻译**

修改概念获取逻辑，当英文用户请求且概念缺少 `text_en` 时触发翻译：

```python
from backend.services.concept_translation import translate_concept_if_needed

@router.get("/{concept_id}")
def get_concept(concept_id: str):
    lang = get_language()
    concept = db.concepts.get(concept_id)
    if not concept:
        return {"error": "Concept not found"}

    # 英文用户且概念缺少英文名时，触发翻译
    if lang == "en" and not concept.get("text_en"):
        translate_concept_if_needed(concept, db)
        concept = db.concepts.get(concept_id)  # 重新获取更新后的概念

    return localize_concept(concept, lang)
```

注意：翻译是异步/耗时的操作，不应该阻塞响应。翻译失败时降级显示中文名（已在 `translate_concept_if_needed` 中处理）。

- [ ] **Step 2: Commit**

```bash
git add backend/routes/concepts.py
git commit -m "feat: auto-translate concept names missing text_en on demand"
```

---

### Task 10: 端到端验证测试

- [ ] **Step 1: 启动前后端**

后端：
```bash
cd D:\meta-knowledge-graph-main
venv/Scripts/activate
python -m uvicorn backend.main:app --reload --port 8089
```

前端：
```bash
cd D:\meta-knowledge-graph-main\frontend
npm run dev
```

- [ ] **Step 2: 手动测试清单**

1. **语言切换**：点击语言切换按钮，确认 UI 文本从中文切换到英文
2. **概念名跟随语言**：切换英文后，概念图谱中概念名显示英文版本
3. **搜索使用英文**：打开浏览器开发者工具 Network 面板，触发"发现研究点"，检查 S2 API 请求的 query 参数是否为英文
4. **历史概念翻译**：如果有缺少 `text_en` 的历史概念，切换英文查看是否触发翻译
5. **API 请求头**：Network 面板检查请求是否携带 `Accept-Language: en` 或 `Accept-Language: zh`

- [ ] **Step 3: Commit（如有修复）**

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/i18n/index.tsx` | 修改 | 导出 getLanguage() |
| `frontend/src/lib/api/client.ts` | 修改 | 添加 Accept-Language interceptor |
| `frontend/src/lib/concept.ts` | 新建 | getConceptDisplayName 工具 |
| `frontend/src/components/ConceptGraphInChat.tsx` | 修改 | 语言感知概念名 |
| `frontend/src/components/MiniConceptGraph.tsx` | 修改 | 语言感知概念名 |
| `frontend/src/components/cards/ResearchPointsCard.tsx` | 修改 | 语言感知概念名 |
| `backend/dependencies.py` | 修改 | 添加语言 ContextVar |
| `backend/main.py` | 修改 | 注册语言中间件 |
| `backend/services/localization.py` | 新建 | 概念本地化工具 |
| `backend/services/concept_translation.py` | 新建 | 概念翻译服务 |
| `backend/services/research_service.py` | 修改 | 搜索/研究点使用英文 |
| `backend/routes/concepts.py` | 修改 | 响应本地化 + 按需翻译 |
| `backend/routes/concepts_tree.py` | 修改 | 响应本地化 |
| `mkg/database.py` | 修改 | get_concept_by_text 支持英文搜索 |
| `mkg/agent/tools.py` | 修改 | 搜索使用 text_en |
