# Semantic Scholar 元数据增强功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 上传 PDF 时自动调用 Semantic Scholar API 查询论文信息，增强元数据。

**Architecture:** 后端新增 `mkg/semantic_scholar.py` API 客户端模块，`backend/routes/semantic_scholar.py` 配置路由；修改 `mkg/database.py` 新增表字段；修改 `backend/routes/papers.py` 集成增强流程；前端新增配置组件。

**Tech Stack:** Python 3.10+, FastAPI, SQLite, React 18, TypeScript, TailwindCSS

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `mkg/database.py` | 修改 | 新增 papers 表字段、s2_config 表、配置读写方法 |
| `mkg/semantic_scholar.py` | 新增 | Semantic Scholar API 客户端 |
| `backend/routes/papers.py` | 修改 | 上传流程集成元数据增强 |
| `backend/routes/semantic_scholar.py` | 新增 | 配置管理 API 路由 |
| `backend/main.py` | 修改 | 注册新路由 |
| `backend/schemas.py` | 修改 | 新增 S2 配置响应模型 |
| `frontend/src/lib/api.ts` | 修改 | 新增 S2 API 调用 |
| `frontend/src/components/S2ConfigModal.tsx` | 新增 | 配置界面组件 |
| `frontend/src/pages/Home.tsx` | 修改 | 添加配置入口 |

---

## Task 1: 数据库扩展

**Files:**
- Modify: `mkg/database.py`

- [ ] **Step 1: 在 papers 表新增字段**

在 `_init_tables` 方法的 papers 表 CREATE 语句中，在 `updated_at` 字段后添加：

```python
        # 论文表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                doi TEXT PRIMARY KEY,
                arxiv_id TEXT UNIQUE,
                title TEXT NOT NULL,
                abstract TEXT,
                authors TEXT,  -- JSON array
                keywords TEXT,  -- JSON array - 关键词
                contributions TEXT,  -- JSON array - 创新点
                published_date TEXT,
                pdf_path TEXT,
                status TEXT DEFAULT 'pending',  -- pending/downloaded/processed/failed
                error_message TEXT,
                s2_paper_id TEXT,  -- Semantic Scholar 论文 ID
                venue TEXT,  -- 期刊/会议
                year INTEGER,  -- 发表年份
                citation_count INTEGER,  -- 引用数
                reference_count INTEGER,  -- 参考文献数
                influential_citation_count INTEGER,  -- 影响力引用数
                open_access_pdf TEXT,  -- 开放获取 PDF 信息 (JSON)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
```

- [ ] **Step 2: 新增 s2_config 表**

在 `_init_tables` 方法末尾（folders 表之后）添加：

```python
        # Semantic Scholar 配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS s2_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                api_key TEXT,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
```

- [ ] **Step 3: 添加 S2 配置读写方法**

在 `Database` 类末尾添加：

```python
    # ==================== Semantic Scholar Config ====================

    def get_s2_config(self) -> Optional[Dict]:
        """获取 Semantic Scholar 配置"""
        cursor = self.execute_read("SELECT * FROM s2_config WHERE id = 1")
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def save_s2_config(self, api_key: str, enabled: bool = True) -> Dict:
        """保存 Semantic Scholar 配置"""
        cursor = self.execute_write("""
            INSERT INTO s2_config (id, api_key, enabled, updated_at)
            VALUES (1, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                api_key = excluded.api_key,
                enabled = excluded.enabled,
                updated_at = CURRENT_TIMESTAMP
        """, (api_key, enabled))
        return self.get_s2_config()
```

- [ ] **Step 4: 添加数据库迁移逻辑**

在 `_init_tables` 方法最后添加（处理已有数据库）：

```python
        # 迁移：为已存在的 papers 表添加新字段
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN s2_paper_id TEXT")
        except sqlite3.OperationalError:
            pass  # 字段已存在
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN venue TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN year INTEGER")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN citation_count INTEGER")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN reference_count INTEGER")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN influential_citation_count INTEGER")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN open_access_pdf TEXT")
        except sqlite3.OperationalError:
            pass

        self.conn.commit()
```

- [ ] **Step 5: 验证数据库修改**

运行后端检查表结构：

```bash
cd D:/meta-knowledge-graph-main && python -c "from mkg.database import Database; db = Database('mkg.db'); db.connect(); print('Tables OK')"
```

Expected: 无报错，输出 "Tables OK"

- [ ] **Step 6: Commit**

```bash
git add mkg/database.py
git commit -m "feat(db): add S2 metadata fields and config table"
```

---

## Task 2: Semantic Scholar API 客户端模块

**Files:**
- Create: `mkg/semantic_scholar.py`

- [ ] **Step 1: 创建 API 客户端模块**

创建 `mkg/semantic_scholar.py`：

```python
"""
Semantic Scholar API 客户端
"""

import requests
import time
import json
from typing import Optional, Dict, List


class SemanticScholarClient:
    """Semantic Scholar API 客户端"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"x-api-key": api_key}
        self.last_request_time = 0

    def _wait_for_rate_limit(self):
        """速率限制：1 request/second"""
        elapsed = time.time() - self.last_request_time
        if elapsed < 1.1:
            time.sleep(1.1 - elapsed)
        self.last_request_time = time.time()

    def search_by_title(self, title: str) -> Optional[Dict]:
        """
        用标题搜索论文，返回第一个匹配结果

        Args:
            title: 论文标题

        Returns:
            匹配的论文信息，包含：
            - paperId: S2 论文 ID
            - title: 标题
            - abstract: 摘要
            - authors: 作者列表
            - year: 发表年份
            - venue: 期刊/会议
            - citationCount: 引用数
            - referenceCount: 参考文献数
            - influentialCitationCount: 影响力引用数
            - openAccessPdf: 开放获取 PDF 信息
        """
        if not title or len(title.strip()) < 3:
            return None

        self._wait_for_rate_limit()

        params = {
            "query": title,
            "fields": "paperId,title,abstract,authors,year,venue,citationCount,referenceCount,influentialCitationCount,openAccessPdf",
            "limit": 1
        }

        try:
            response = requests.get(
                f"{self.BASE_URL}/paper/search/bulk",
                params=params,
                headers=self.headers,
                timeout=10
            )

            if response.status_code != 200:
                return None

            data = response.json()
            if not data.get("data"):
                return None

            return data["data"][0]

        except Exception as e:
            print(f"Semantic Scholar API error: {e}")
            return None

    def enhance_paper_data(self, title: str, existing_data: Optional[Dict] = None) -> Dict:
        """
        增强论文数据

        Args:
            title: 论文标题
            existing_data: 已有的论文数据（用于合并）

        Returns:
            增强后的论文数据字典
        """
        s2_result = self.search_by_title(title)

        result = existing_data.copy() if existing_data else {}

        if s2_result:
            # 只在 S2 有数据时覆盖
            result['s2_paper_id'] = s2_result.get('paperId')

            if s2_result.get('abstract'):
                result['abstract'] = s2_result['abstract']

            if s2_result.get('authors'):
                result['authors'] = [a['name'] for a in s2_result['authors'] if 'name' in a]

            if s2_result.get('venue'):
                result['venue'] = s2_result['venue']

            if s2_result.get('year'):
                result['year'] = s2_result['year']

            if s2_result.get('citationCount') is not None:
                result['citation_count'] = s2_result['citationCount']

            if s2_result.get('referenceCount') is not None:
                result['reference_count'] = s2_result['referenceCount']

            if s2_result.get('influentialCitationCount') is not None:
                result['influential_citation_count'] = s2_result['influentialCitationCount']

            if s2_result.get('openAccessPdf'):
                result['open_access_pdf'] = json.dumps(s2_result['openAccessPdf'])

        return result

    @staticmethod
    def test_connection(api_key: str) -> Dict:
        """
        测试 API Key 是否有效

        Returns:
            {"success": bool, "message": str}
        """
        headers = {"x-api-key": api_key}

        try:
            response = requests.get(
                "https://api.semanticscholar.org/graph/v1/paper/search/bulk",
                params={"query": "test", "limit": 1},
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                return {"success": True, "message": "API Key 有效"}
            elif response.status_code == 401:
                return {"success": False, "message": "API Key 无效"}
            else:
                return {"success": False, "message": f"请求失败: {response.status_code}"}

        except Exception as e:
            return {"success": False, "message": f"连接失败: {str(e)}"}
```

- [ ] **Step 2: 验证模块可导入**

```bash
cd D:/meta-knowledge-graph-main && python -c "from mkg.semantic_scholar import SemanticScholarClient; print('Module OK')"
```

Expected: 输出 "Module OK"

- [ ] **Step 3: Commit**

```bash
git add mkg/semantic_scholar.py
git commit -m "feat(s2): add Semantic Scholar API client module"
```

---

## Task 3: 后端 S2 配置路由

**Files:**
- Create: `backend/routes/semantic_scholar.py`
- Modify: `backend/schemas.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 新增 Schema 模型**

在 `backend/schemas.py` 末尾添加：

```python
# Semantic Scholar Configuration schemas
class S2ConfigResponse(BaseModel):
    """S2 配置响应"""
    has_api_key: bool
    enabled: bool
    masked_key: Optional[str] = None  # 脱敏后的 API Key


class S2ConfigRequest(BaseModel):
    """S2 配置请求"""
    api_key: str
    enabled: bool = True


class S2TestResponse(BaseModel):
    """S2 连接测试响应"""
    success: bool
    message: str
```

- [ ] **Step 2: 创建路由文件**

创建 `backend/routes/semantic_scholar.py`：

```python
"""
Semantic Scholar API routes
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mkg.database import Database
from mkg.semantic_scholar import SemanticScholarClient
from backend.schemas import S2ConfigResponse, S2ConfigRequest, S2TestResponse

router = APIRouter(prefix="/api/s2", tags=["semantic-scholar"])

_db = None


def get_db():
    global _db
    if _db is None:
        _db = Database("mkg.db")
        _db.connect()
    return _db


@router.get("/config", response_model=S2ConfigResponse)
def get_config():
    """获取 Semantic Scholar 配置状态"""
    db = get_db()
    config = db.get_s2_config()

    if not config or not config.get('api_key'):
        return S2ConfigResponse(has_api_key=False, enabled=True)

    # 脱敏处理 API Key
    key = config['api_key']
    masked = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"

    return S2ConfigResponse(
        has_api_key=True,
        enabled=config.get('enabled', True),
        masked_key=masked
    )


@router.post("/config", response_model=S2ConfigResponse)
def save_config(request: S2ConfigRequest):
    """保存 Semantic Scholar API Key"""
    db = get_db()
    config = db.save_s2_config(request.api_key, request.enabled)

    key = request.api_key
    masked = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"

    return S2ConfigResponse(
        has_api_key=True,
        enabled=config['enabled'],
        masked_key=masked
    )


@router.post("/test", response_model=S2TestResponse)
def test_connection(request: S2ConfigRequest):
    """测试 API Key 是否有效"""
    result = SemanticScholarClient.test_connection(request.api_key)
    return S2TestResponse(success=result['success'], message=result['message'])


@router.post("/papers/{doi:path}/enhance")
def enhance_paper(doi: str):
    """手动重新增强指定论文的元数据"""
    db = get_db()
    paper = db.get_paper(doi)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    config = db.get_s2_config()
    if not config or not config.get('api_key'):
        raise HTTPException(status_code=400, detail="Semantic Scholar API Key not configured")

    if not paper.get('title'):
        raise HTTPException(status_code=400, detail="Paper has no title to search")

    client = SemanticScholarClient(config['api_key'])
    enhanced = client.enhance_paper_data(paper['title'], {})

    if enhanced:
        # 更新数据库
        update_fields = []
        update_values = []
        for field in ['s2_paper_id', 'abstract', 'authors', 'venue', 'year',
                       'citation_count', 'reference_count', 'influential_citation_count', 'open_access_pdf']:
            if field in enhanced:
                update_fields.append(f"{field} = ?")
                update_values.append(enhanced[field])

        if update_fields:
            update_values.append(doi)
            db.execute_write(
                f"UPDATE papers SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE doi = ?",
                tuple(update_values)
            )

    return {"success": True, "enhanced": enhanced}
```

- [ ] **Step 3: 注册路由**

在 `backend/main.py` 中添加导入和注册：

```python
# 在导入部分添加
from backend.routes import papers, concepts, graph, llm, folders, semantic_scholar

# 在路由注册部分添加
app.include_router(semantic_scholar.router)
```

- [ ] **Step 4: 验证路由可用**

```bash
cd D:/meta-knowledge-graph-main && python -c "from backend.main import app; print('Routes OK')"
```

Expected: 输出 "Routes OK"

- [ ] **Step 5: Commit**

```bash
git add backend/routes/semantic_scholar.py backend/schemas.py backend/main.py
git commit -m "feat(api): add S2 config routes"
```

---

## Task 4: 论文上传流程集成元数据增强

**Files:**
- Modify: `backend/routes/papers.py`

- [ ] **Step 1: 添加导入**

在 `backend/routes/papers.py` 文件顶部的导入部分添加：

```python
from mkg.semantic_scholar import SemanticScholarClient
```

- [ ] **Step 2: 添加 S2 增强辅助函数**

在 `get_extractor()` 函数之后添加：

```python
def get_s2_client():
    """获取 Semantic Scholar 客户端（如果已配置）"""
    db = get_db()
    config = db.get_s2_config()
    if config and config.get('api_key') and config.get('enabled', True):
        return SemanticScholarClient(config['api_key'])
    return None
```

- [ ] **Step 3: 修改 upload_paper 函数**

在 `upload_paper` 函数中，找到 `doi = db.add_paper(paper_data)` 这一行，在其之前添加 S2 增强逻辑：

```python
    # Semantic Scholar 元数据增强
    s2_client = get_s2_client()
    if s2_client and paper_data.get('title'):
        try:
            paper_data = s2_client.enhance_paper_data(paper_data['title'], paper_data)
        except Exception as e:
            print(f"S2 enhancement failed: {e}")  # 静默失败

    doi = db.add_paper(paper_data)
```

- [ ] **Step 4: 修改 batch_upload_papers 函数**

在 `batch_upload_papers` 函数中，找到 `doi = db.add_paper(paper_data)` 这一行，在其之前添加：

```python
            # Semantic Scholar 元数据增强
            s2_client = get_s2_client()
            if s2_client and paper_data.get('title'):
                try:
                    paper_data = s2_client.enhance_paper_data(paper_data['title'], paper_data)
                except Exception as e:
                    print(f"S2 enhancement failed: {e}")  # 静默失败

            doi = db.add_paper(paper_data)
```

- [ ] **Step 5: 修改 Database.add_paper 方法**

打开 `mkg/database.py`，找到 `add_paper` 方法，确保它支持新字段。查找该方法并确认参数处理：

如果 `add_paper` 方法使用了明确的字段列表，需要添加新字段。当前应该类似：

```python
def add_paper(self, paper_data: dict) -> str:
    # 确保方法能处理新字段
```

检查并确认方法能接收并存储 `s2_paper_id`, `venue`, `year`, `citation_count`, `reference_count`, `influential_citation_count`, `open_access_pdf` 字段。

- [ ] **Step 6: 验证修改**

```bash
cd D:/meta-knowledge-graph-main && python -c "from backend.routes.papers import get_s2_client; print('S2 integration OK')"
```

Expected: 输出 "S2 integration OK"

- [ ] **Step 7: Commit**

```bash
git add backend/routes/papers.py
git commit -m "feat(papers): integrate S2 metadata enhancement on upload"
```

---

## Task 5: 前端 API 扩展

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: 添加 S2 API 类型定义**

在 `frontend/src/lib/api.ts` 文件的类型定义部分添加（在 LLM 相关类型之后）：

```typescript
// Semantic Scholar Configuration types
interface S2ConfigResponse {
  has_api_key: boolean
  enabled: boolean
  masked_key?: string
}

interface S2ConfigRequest {
  api_key: string
  enabled?: boolean
}

interface S2TestResponse {
  success: boolean
  message: string
}
```

- [ ] **Step 2: 添加 S2 API 方法**

在 `llmApi` 之后添加：

```typescript
// Semantic Scholar API
export const s2Api = {
  getConfig: () => api.get<S2ConfigResponse>('/s2/config'),
  saveConfig: (data: S2ConfigRequest) => api.post<S2ConfigResponse>('/s2/config', data),
  test: (apiKey: string) => api.post<S2TestResponse>('/s2/test', { api_key: apiKey }),
  enhance: (doi: string) => api.post(`/s2/papers/${encodeURIComponent(doi)}/enhance`),
}
```

- [ ] **Step 3: 导出新类型**

在文件末尾的 export type 行添加：

```typescript
export type { PaperContribution, ProcessSingleResponse, ScanStatusResponse, S2ConfigResponse, S2ConfigRequest, S2TestResponse }
```

- [ ] **Step 4: 验证 TypeScript 编译**

```bash
cd D:/meta-knowledge-graph-main/frontend && npx tsc --noEmit
```

Expected: 无错误输出

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat(frontend): add S2 API client"
```

---

## Task 6: S2 配置组件

**Files:**
- Create: `frontend/src/components/S2ConfigModal.tsx`

- [ ] **Step 1: 创建配置组件**

创建 `frontend/src/components/S2ConfigModal.tsx`：

```tsx
import { useEffect, useState } from 'react'
import { X, Check, Loader2, Database } from 'lucide-react'
import { s2Api } from '../lib/api'

interface Props {
  onClose: () => void
  onSave: () => void
}

export default function S2ConfigModal({ onClose, onSave }: Props) {
  const [apiKey, setApiKey] = useState('')
  const [enabled, setEnabled] = useState(true)
  const [hasKey, setHasKey] = useState(false)
  const [maskedKey, setMaskedKey] = useState<string | null>(null)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    s2Api.getConfig().then(res => {
      setHasKey(res.data.has_api_key)
      setEnabled(res.data.enabled)
      setMaskedKey(res.data.masked_key || null)
    }).catch(() => {
      setHasKey(false)
    })
  }, [])

  const handleTest = async () => {
    if (!apiKey) return
    setTesting(true)
    setTestResult(null)
    try {
      const res = await s2Api.test(apiKey)
      setTestResult({ success: res.data.success, message: res.data.message })
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || '测试失败'
      setTestResult({ success: false, message: errorMsg })
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    if (!apiKey && !hasKey) return
    setSaving(true)
    try {
      await s2Api.saveConfig({ api_key: apiKey, enabled })
      onSave()
    } catch (err) {
      alert('保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5 text-purple-600" />
            <h2 className="text-lg font-semibold">Semantic Scholar 配置</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Status */}
          {hasKey && maskedKey && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700">
              <Check className="inline h-4 w-4 mr-1" />
              已配置 API Key: {maskedKey}
            </div>
          )}

          {/* API Key */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              API Key {!hasKey && <span className="text-red-500">*</span>}
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={e => {
                setApiKey(e.target.value)
                setTestResult(null)
              }}
              placeholder={hasKey ? "输入新 Key 更换" : "输入 Semantic Scholar API Key"}
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">
              申请地址: <a href="https://www.semanticscholar.org/product/api" target="_blank" className="text-purple-600 hover:underline">Semantic Scholar API</a>
            </p>
          </div>

          {/* Enable Switch */}
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700">
              启用自动增强
            </label>
            <button
              onClick={() => setEnabled(!enabled)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                enabled ? 'bg-purple-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Test Result */}
          {testResult && (
            <div className={`rounded-lg p-3 text-sm ${
              testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
            }`}>
              {testResult.message}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-2 p-4 border-t bg-gray-50">
          <button
            onClick={handleTest}
            disabled={testing || !apiKey}
            className="flex-1 py-2 px-4 rounded-lg border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-50"
          >
            {testing ? <Loader2 className="inline h-4 w-4 animate-spin mr-1" /> : null}
            测试连接
          </button>
          <button
            onClick={handleSave}
            disabled={saving || (!apiKey && !hasKey)}
            className="flex-1 py-2 px-4 rounded-lg bg-purple-600 text-white text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
          >
            {saving ? '保存中...' : '保存配置'}
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/S2ConfigModal.tsx
git commit -m "feat(frontend): add S2 config modal component"
```

---

## Task 7: 集成配置入口到 Home 页面

**Files:**
- Modify: `frontend/src/pages/Home.tsx`

- [ ] **Step 1: 添加导入**

在 `frontend/src/pages/Home.tsx` 文件顶部添加导入：

```tsx
import S2ConfigModal from '../components/S2ConfigModal'
import { s2Api } from '../lib/api'
```

- [ ] **Step 2: 添加状态变量**

在 `const [showLLMModal, setShowLLMModal] = useState(false)` 之后添加：

```tsx
  const [s2Status, setS2Status] = useState<string>('')
  const [showS2Modal, setShowS2Modal] = useState(false)
```

- [ ] **Step 3: 添加 S2 状态加载**

在 `useEffect` 加载 LLM 状态的后面，添加 S2 状态加载：

```tsx
  useEffect(() => {
    s2Api.getConfig().then(res => {
      if (res.data.has_api_key) {
        setS2Status(res.data.enabled ? '已启用' : '已禁用')
      } else {
        setS2Status('未配置')
      }
    }).catch(() => setS2Status('未配置'))
  }, [])
```

- [ ] **Step 4: 添加配置按钮**

在快速操作区域（LLM 配置按钮之后），添加 S2 配置按钮：

```tsx
          <button
            onClick={() => setShowS2Modal(true)}
            className="flex items-center p-4 bg-brand-fill rounded-xl hover:shadow-brand transition-all text-left"
          >
            <div className="h-10 w-10 bg-brand-button rounded-lg flex items-center justify-center mr-3">
              <Database className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-medium text-brand-700">S2 配置</p>
              <p className="text-sm text-brand-500">{s2Status || '配置元数据增强'}</p>
            </div>
          </button>
```

同时在导入中添加 `Database` 图标：

```tsx
import { FileText, GitBranch, Network, TrendingUp, Settings, Database } from 'lucide-react'
```

- [ ] **Step 5: 添加 S2 Modal 渲染**

在 LLM Config Modal 之后添加：

```tsx
      {/* S2 Config Modal */}
      {showS2Modal && (
        <S2ConfigModal
          onClose={() => setShowS2Modal(false)}
          onSave={() => {
            setShowS2Modal(false)
            s2Api.getConfig().then(res => {
              if (res.data.has_api_key) {
                setS2Status(res.data.enabled ? '已启用' : '已禁用')
              } else {
                setS2Status('未配置')
              }
            })
          }}
        />
      )}
```

- [ ] **Step 6: 验证前端编译**

```bash
cd D:/meta-knowledge-graph-main/frontend && npm run build
```

Expected: 编译成功，无错误

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Home.tsx
git commit -m "feat(frontend): add S2 config entry to home page"
```

---

## Task 8: 集成测试

- [ ] **Step 1: 启动后端服务**

```bash
cd D:/meta-knowledge-graph-main && python -m uvicorn backend.main:app --port 8088 --reload
```

- [ ] **Step 2: 启动前端服务（新终端）**

```bash
cd D:/meta-knowledge-graph-main/frontend && npm run dev
```

- [ ] **Step 3: 测试 S2 配置**

1. 打开 http://localhost:5173
2. 点击 "S2 配置" 按钮
3. 输入 API Key: `HdvhTeK6be5JUDCMKhwXa66QibQ2Qn171FL0Kkns`
4. 点击 "测试连接" - 应显示 "API Key 有效"
5. 点击 "保存配置"

- [ ] **Step 4: 测试论文上传增强**

1. 进入 Papers 页面
2. 上传一个已知的论文 PDF（如 "Attention is All You Need" 或任何有明确标题的论文）
3. 上传后检查论文详情，验证是否有：
   - 发表年份 (year)
   - 期刊/会议 (venue)
   - 引用数 (citation_count)
   - S2 Paper ID (s2_paper_id)

- [ ] **Step 5: 测试无 API Key 场景**

1. 清除 S2 配置（API Key 留空保存）
2. 上传论文，验证不报错，正常处理

---

## 验证清单

- [ ] 数据库新增字段正确创建
- [ ] S2 配置可正常保存和读取
- [ ] API Key 测试功能正常
- [ ] 论文上传时自动增强元数据
- [ ] 无 API Key 时不影响正常上传
- [ ] 前端配置界面正常工作