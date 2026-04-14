# 多语言国际化设计

> **需求：** 完整的中文/英文双语支持，用户可切换语言。搜索始终使用英文以确保 Semantic Scholar 搜索质量。概念名跟随用户语言，其他内容（研究点、论文摘要等）保持原始语言。

---

## 现状分析

**已有能力（不需要新建）：**

1. **概念提取 prompt 已是双语**：`STAGE2_EXTRACTION_PROMPT` 要求 LLM 输出 `{"en": "...", "zh": "..."}` 格式
2. **存储层已支持双语**：`concepts` 表有 `text`（优先中文）、`text_en`（英文）、`text_zh`（中文）三列
3. **前端已有 i18n 切换**：`zh.ts`/`en.ts` + localStorage 持久化

**当前问题（需要修复）：**

| 问题 | 位置 | 原因 |
|------|------|------|
| S2 搜索用中文 | `research_service.py:search_papers_by_concept` | `query = concept["text"]` 是中文 |
| 研究点 prompt 用中文 | `research_service.py:_build_research_prompt` | 上下文用 `c['text']`（中文） |
| 前端概念名不跟随语言 | 各组件直接用 `concept.concept`/`concept.text` | 没有根据 i18n 语言选择 `text_en` |
| 英文用户搜不到概念 | `database.py:get_concept_by_text` | 只搜索 `text` 列，不搜索 `text_en` |

---

## 架构决策

采用 **方案 B：语言上下文传播**

- 前端所有 API 请求携带 `Accept-Language` 头
- 后端解析语言头，在响应中统一适配概念名
- 搜索始终使用英文（`text_en`）
- 概念名双语存储，其他内容不翻译

---

## 架构图

```
用户切换语言 (zh/en)
  ↓
前端 API Client 自动添加 Accept-Language 头
  ↓
后端中间件解析语言，注入 request context
  ↓
API 响应层：localize_concept() 适配概念名
搜索层：始终使用英文概念名
研究点：prompt 使用英文上下文
  ↓
返回适配后的数据到前端
```

---

## 组件变更

### 前端

#### 1. API Client 自动携带语言头

**文件：** `frontend/src/lib/api/client.ts`

添加 axios interceptor，自动在请求头添加 `Accept-Language`：

```typescript
import { getLanguage } from '../../i18n';

axios.interceptors.request.use((config) => {
  config.headers['Accept-Language'] = getLanguage();
  return config;
});
```

需要在 `i18n/index.tsx` 中导出 `getLanguage()` 函数：

```typescript
export function getLanguage(): string {
  return typeof window !== 'undefined'
    ? (localStorage.getItem(LANGUAGE_KEY) || 'zh')
    : 'zh';
}
```

#### 2. 概念名展示逻辑

所有渲染概念名的组件改为语言感知：

```typescript
const displayName = (concept: Concept) => {
  const lang = getLanguage();
  if (lang === 'en' && concept.text_en) {
    return concept.text_en;
  }
  return concept.concept;
};
```

影响的文件/组件：
- `frontend/src/pages/ConceptsGraph/index.tsx`
- `frontend/src/components/ConceptGraphInChat.tsx`
- `frontend/src/components/cards/ResearchPointsCard.tsx`
- `frontend/src/components/MiniConceptGraph.tsx`
- `frontend/src/components/Sidebar.tsx`（概念列表）

#### 3. i18n 翻译文件扩展

**文件：** `frontend/src/i18n/zh.ts`, `frontend/src/i18n/en.ts`

确保所有 UI 文本都有双语翻译。当前已有基础翻译，需补充：
- 研究点卡片相关文本
- 概念图谱页面文本
- 论文处理页面文本
- 错误提示信息

---

### 后端

#### 1. 语言中间件

**文件：** `backend/dependencies.py`（工具函数），`backend/main.py`（middleware 注册）

`dependencies.py` 中定义 ContextVar 和依赖注入函数：

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

`main.py` 中注册 middleware：

```python
from backend.dependencies import set_language

@app.middleware("http")
async def language_middleware(request: Request, call_next):
    lang = request.headers.get("Accept-Language", "zh")[:2]
    if lang not in ("zh", "en"):
        lang = "zh"
    set_language(lang)
    response = await call_next(request)
    return response
```

#### 2. 概念本地化工具函数

**文件：** `backend/services/localization.py`（新建）

```python
def localize_concept(concept: dict, lang: str) -> dict:
    """根据语言返回对应的概念名"""
    if lang == "en" and concept.get("text_en"):
        return {**concept, "text": concept["text_en"]}
    return concept

def localize_concept_list(concepts: list[dict], lang: str) -> list[dict]:
    """批量本地化概念列表"""
    return [localize_concept(c, lang) for c in concepts]
```

#### 4. get_concept_by_text 支持英文搜索

**文件：** `mkg/database.py`

当前 `get_concept_by_text` 只搜索 `text` 列，英文用户用英文名找不到概念。需要同时搜索 `text_en`：

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

#### 5. 概念 API 适配

**文件：** `backend/routes/concepts.py`, `backend/routes/concepts_tree.py`

所有返回概念数据的端点，在返回前调用 `localize_concept`：

```python
@router.get("/{concept_id}")
def get_concept(concept_id: str, lang: str = Depends(get_language)):
    concept = db.concepts.get(concept_id)
    return localize_concept(concept, lang)
```

#### 6. 搜索始终使用英文

**文件：** `backend/services/research_service.py`

```python
def search_papers_by_concept(self, concept_id: str, ...):
    concept = self.db.concepts.get(concept_id)
    # 始终使用英文概念名搜索
    query = concept.get("text_en") or concept["text"]
    papers = self.s2_client.search_papers(query, limit=limit * 2)
```

#### 7. 研究点发现使用英文 prompt

**文件：** `backend/services/research_service.py`

`_build_research_prompt` 中的概念名优先使用英文：

```python
def _localized_name(c):
    return c.get("text_en") or c.get("text", "")

# 在构建 prompt 时使用 _localized_name
```

---

## 历史数据补全

### 问题

已有概念可能缺少 `text_en` 字段。

### 方案：按需翻译

当用户切换英文 UI 且概念缺少 `text_en` 时：

1. 后端检测到 `text_en` 为空
2. 调用 LLM 翻译中文概念名为英文
3. 保存到数据库
4. 返回翻译后的概念名

**文件：** `backend/services/concept_translation.py`（新建）

```python
def translate_concept_if_needed(concept: dict) -> str:
    """如果概念缺少英文名，自动翻译并保存"""
    if concept.get("text_en"):
        return concept["text_en"]
    
    # 调用 LLM 翻译
    llm = get_llm_or_raise()
    prompt = f"将以下中文学术概念翻译为英文，只返回翻译结果：{concept['text']}"
    response = llm.invoke(prompt)
    en_name = response.content.strip()
    
    # 保存到数据库
    db = get_db()
    db.concepts.update(concept['id'], {"text_en": en_name})
    
    return en_name
```

---

## 错误处理

| 场景 | 处理方式 |
|------|------|
| 概念缺少 `text_en` | 自动触发 LLM 翻译并缓存 |
| LLM 翻译失败 | 降级显示中文概念名，控制台记录警告 |
| S2 API 不可用 | 显示"论文搜索暂时不可用" |
| 搜索结果为空 | 尝试用中文概念名回退搜索 |
| 语言切换中请求未完成 | 不中断，新请求使用新语言 |

---

## 测试策略

### 前端测试

- 语言切换后，所有 UI 文本正确显示
- 切换英文时，概念名显示英文版本
- API 请求携带正确的 `Accept-Language` 头
- 历史概念（无 `text_en`）正确降级显示

### 后端测试

- `localize_concept` 正确选择语言
- 搜索始终使用英文概念名
- 研究点 prompt 使用英文上下文
- 概念翻译中间件正确工作
- 缺少 `text_en` 的概念自动翻译

### 集成测试

- 中文用户完整流程
- 英文用户完整流程
- 语言切换中途的操作

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/lib/api/client.ts` | 修改 | 添加 Accept-Language interceptor |
| `frontend/src/i18n/index.tsx` | 修改 | 导出 getLanguage() |
| `frontend/src/i18n/zh.ts` | 修改 | 补充翻译 |
| `frontend/src/i18n/en.ts` | 修改 | 补充翻译 |
| `frontend/src/pages/ConceptsGraph/index.tsx` | 修改 | 语言感知概念名 |
| `frontend/src/components/ConceptGraphInChat.tsx` | 修改 | 语言感知概念名 |
| `frontend/src/components/MiniConceptGraph.tsx` | 修改 | 语言感知概念名 |
| `frontend/src/components/cards/ResearchPointsCard.tsx` | 修改 | 语言感知概念名 |
| `frontend/src/components/Sidebar.tsx` | 修改 | 语言感知概念名 |
| `backend/dependencies.py` | 修改 | 添加语言中间件 |
| `backend/services/localization.py` | 新建 | 概念本地化工具 |
| `backend/services/concept_translation.py` | 新建 | 概念翻译服务 |
| `backend/services/research_service.py` | 修改 | 搜索/研究点使用英文 |
| `backend/routes/concepts.py` | 修改 | 响应本地化 |
| `backend/routes/concepts_tree.py` | 修改 | 响应本地化 |
| `mkg/agent/tools.py` | 修改 | 搜索使用 text_en |
