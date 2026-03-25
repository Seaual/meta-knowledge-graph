# LLM Configuration Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add LLM configuration UI to homepage with multi-provider support, persisted to SQLite database.

**Architecture:** Database schema for config storage → Backend API for CRUD and testing → Frontend modal UI → Integration with existing LLM code.

**Tech Stack:** SQLite, FastAPI, Pydantic, React, TypeScript, TailwindCSS

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `openclaw/database.py` | Modify | Add llm_config tables and CRUD methods |
| `backend/schemas.py` | Modify | Add LLM config Pydantic models |
| `backend/routes/llm.py` | Create | New API endpoints for LLM config |
| `backend/main.py` | Modify | Include llm router |
| `frontend/src/lib/api.ts` | Modify | Add llmApi |
| `frontend/src/pages/Home.tsx` | Modify | Add LLM config card |
| `frontend/src/components/LLMConfigModal.tsx` | Create | Configuration modal component |
| `backend/routes/papers.py` | Modify | Use database config |
| `backend/routes/concepts.py` | Modify | Use database config |

---

## Task 1: Database Schema and CRUD Methods

**Files:**
- Modify: `openclaw/database.py`

- [ ] **Step 1: Add LLM config tables to `_init_tables` method**

Add after existing table definitions (around line 110):

```python
        # LLM 配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT NOT NULL DEFAULT 'single',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_provider_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_id INTEGER NOT NULL,
                function_group TEXT,
                provider TEXT NOT NULL,
                api_key TEXT,
                base_url TEXT,
                model TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (config_id) REFERENCES llm_config(id)
            )
        """)
```

- [ ] **Step 2: Add LLM config CRUD methods to Database class**

Add at the end of the Database class:

```python
    # ========== LLM Configuration ==========

    def get_llm_config(self) -> Optional[Dict]:
        """Get current LLM configuration"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM llm_config ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return None

        config = dict(row)
        config_id = config['id']

        # Get provider configs
        cursor.execute("SELECT * FROM llm_provider_config WHERE config_id = ?", (config_id,))
        providers = [dict(r) for r in cursor.fetchall()]
        config['providers'] = providers

        return config

    def save_llm_config(self, mode: str, providers: List[Dict]) -> Dict:
        """Save LLM configuration"""
        cursor = self.conn.cursor()

        # Clear existing config
        cursor.execute("DELETE FROM llm_provider_config")
        cursor.execute("DELETE FROM llm_config")

        # Insert new config
        cursor.execute(
            "INSERT INTO llm_config (mode) VALUES (?)",
            (mode,)
        )
        config_id = cursor.lastrowid

        # Insert provider configs
        for p in providers:
            cursor.execute("""
                INSERT INTO llm_provider_config
                (config_id, function_group, provider, api_key, base_url, model, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                config_id,
                p.get('function_group'),
                p['provider'],
                p.get('api_key'),
                p.get('base_url'),
                p.get('model'),
                p.get('is_active', True)
            ))

        self.conn.commit()
        return self.get_llm_config()

    def get_llm_provider_for_function(self, function_group: str) -> Optional[Dict]:
        """Get provider config for a specific function"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.* FROM llm_provider_config p
            JOIN llm_config c ON p.config_id = c.id
            WHERE c.mode = 'per_function' AND p.function_group = ? AND p.is_active = 1
        """, (function_group,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_active_llm_provider(self) -> Optional[Dict]:
        """Get the active provider (for single mode)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.* FROM llm_provider_config p
            JOIN llm_config c ON p.config_id = c.id
            WHERE c.mode = 'single' AND p.is_active = 1
            LIMIT 1
        """)
        row = cursor.fetchone()
        return dict(row) if row else None
```

- [ ] **Step 3: Commit database changes**

```bash
git add openclaw/database.py
git commit -m "feat(database): add LLM config tables and CRUD methods"
```

---

## Task 2: Backend Schemas

**Files:**
- Modify: `backend/schemas.py`

- [ ] **Step 1: Add LLM config Pydantic models**

Add at the end of `backend/schemas.py`:

```python
# LLM Configuration schemas
class LLMProviderConfig(BaseModel):
    """单个 LLM 服务商配置"""
    function_group: Optional[str] = None  # paper_parsing, concept_extraction, research_analysis
    provider: str  # openai, anthropic, google, dashscope, openrouter, minimax, claude_cli
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    is_active: bool = True


class LLMConfigResponse(BaseModel):
    """LLM 配置响应"""
    mode: str  # single, per_function
    providers: List[LLMProviderConfig]


class LLMConfigRequest(BaseModel):
    """LLM 配置请求"""
    mode: str
    providers: List[LLMProviderConfig]


class LLMTestRequest(BaseModel):
    """LLM 连接测试请求"""
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class LLMTestResponse(BaseModel):
    """LLM 连接测试响应"""
    success: bool
    message: str
    model: Optional[str] = None
```

- [ ] **Step 2: Commit schema changes**

```bash
git add backend/schemas.py
git commit -m "feat(schemas): add LLM configuration Pydantic models"
```

---

## Task 3: Backend API Routes

**Files:**
- Create: `backend/routes/llm.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create `backend/routes/llm.py`**

```python
"""
LLM Configuration API routes
"""

from fastapi import APIRouter, HTTPException
from typing import List
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from openclaw.database import Database
from openclaw.pdf_parser import AnthropicClient, GoogleClient, OpenAICompatibleClient, ClaudeCLIClient
from backend.schemas import (
    LLMConfigResponse, LLMConfigRequest, LLMTestRequest, LLMTestResponse, LLMProviderConfig
)

router = APIRouter(prefix="/api/llm", tags=["llm"])

_db = None


def get_db():
    global _db
    if _db is None:
        _db = Database("openclaw.db")
        _db.connect()
    return _db


# Available providers
PROVIDERS = [
    {"value": "claude_cli", "label": "Claude Code CLI", "requires_api_key": False},
    {"value": "openai", "label": "OpenAI 兼容接口", "requires_api_key": True, "default_base_url": "https://api.openai.com/v1"},
    {"value": "anthropic", "label": "Anthropic Claude", "requires_api_key": True},
    {"value": "google", "label": "Google Gemini", "requires_api_key": True},
    {"value": "dashscope", "label": "阿里云 DashScope", "requires_api_key": True},
    {"value": "openrouter", "label": "OpenRouter", "requires_api_key": True, "default_base_url": "https://openrouter.ai/api/v1"},
    {"value": "minimax", "label": "MiniMax", "requires_api_key": True},
]

FUNCTION_GROUPS = [
    {"value": "paper_parsing", "label": "论文解析"},
    {"value": "concept_extraction", "label": "概念提取"},
    {"value": "research_analysis", "label": "研究分析"},
]


@router.get("/providers")
def list_providers():
    """List available LLM providers"""
    return {"providers": PROVIDERS, "function_groups": FUNCTION_GROUPS}


@router.get("/config", response_model=LLMConfigResponse)
def get_config():
    """Get current LLM configuration"""
    db = get_db()
    config = db.get_llm_config()

    if not config:
        return LLMConfigResponse(mode="single", providers=[])

    return LLMConfigResponse(
        mode=config['mode'],
        providers=[LLMProviderConfig(**p) for p in config.get('providers', [])]
    )


@router.post("/config", response_model=LLMConfigResponse)
def save_config(request: LLMConfigRequest):
    """Save LLM configuration"""
    db = get_db()

    providers_data = [p.model_dump() for p in request.providers]
    config = db.save_llm_config(request.mode, providers_data)

    return LLMConfigResponse(
        mode=config['mode'],
        providers=[LLMProviderConfig(**p) for p in config.get('providers', [])]
    )


@router.post("/test", response_model=LLMTestResponse)
def test_connection(request: LLMTestRequest):
    """Test LLM connection"""
    try:
        if request.provider == "claude_cli":
            client = ClaudeCLIClient()
            result = client.extract_concepts("Say 'OK' if you can read this.")
            return LLMTestResponse(success=True, message="Claude CLI 连接成功", model="claude-code")

        elif request.provider == "openai":
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key 是必需的")
            client = OpenAICompatibleClient(
                request.api_key,
                base_url=request.base_url or "https://api.openai.com/v1",
                model=request.model or "gpt-3.5-turbo"
            )
            result = client.extract_concepts("Say 'OK' if you can read this.")
            return LLMTestResponse(success=True, message="OpenAI 连接成功", model=request.model)

        elif request.provider == "anthropic":
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key 是必需的")
            client = AnthropicClient(
                request.api_key,
                model=request.model or "claude-sonnet-4-20250514",
                base_url=request.base_url
            )
            result = client.extract_concepts("Say 'OK' if you can read this.")
            return LLMTestResponse(success=True, message="Anthropic 连接成功", model=request.model)

        elif request.provider == "google":
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key 是必需的")
            client = GoogleClient(request.api_key)
            result = client.extract_concepts("Say 'OK' if you can read this.")
            return LLMTestResponse(success=True, message="Google Gemini 连接成功", model="gemini")

        elif request.provider in ("dashscope", "openrouter", "minimax"):
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key 是必需的")
            base_urls = {
                "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "openrouter": "https://openrouter.ai/api/v1",
                "minimax": request.base_url
            }
            client = OpenAICompatibleClient(
                request.api_key,
                base_url=base_urls.get(request.provider, request.base_url),
                model=request.model or "qwen-plus"
            )
            result = client.extract_concepts("Say 'OK' if you can read this.")
            return LLMTestResponse(success=True, message=f"{request.provider} 连接成功", model=request.model)

        else:
            raise HTTPException(status_code=400, detail=f"未知的服务商: {request.provider}")

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
            raise HTTPException(status_code=401, detail="API Key 无效，请检查后重试")
        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            raise HTTPException(status_code=503, detail="网络连接失败，请检查 Base URL")
        elif "model" in error_msg.lower() or "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="模型不存在，请确认模型名称")
        else:
            raise HTTPException(status_code=500, detail=f"测试失败: {error_msg}")
```

- [ ] **Step 2: Add llm router to `backend/main.py`**

Add import and router inclusion:

```python
from backend.routes import papers, concepts, graph, llm

# ... in the router section:
app.include_router(llm.router)
```

- [ ] **Step 3: Commit backend API changes**

```bash
git add backend/routes/llm.py backend/main.py
git commit -m "feat(backend): add LLM configuration API endpoints"
```

---

## Task 4: Frontend API Client

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add LLM API types and methods**

Add at the end of `frontend/src/lib/api.ts`:

```typescript
// LLM Configuration types
interface LLMProviderConfig {
  function_group?: string
  provider: string
  api_key?: string
  base_url?: string
  model?: string
  is_active: boolean
}

interface LLMConfigResponse {
  mode: string
  providers: LLMProviderConfig[]
}

interface LLMTestResponse {
  success: boolean
  message: string
  model?: string
}

interface ProviderInfo {
  value: string
  label: string
  requires_api_key: boolean
  default_base_url?: string
}

interface FunctionGroup {
  value: string
  label: string
}

// LLM API
export const llmApi = {
  providers: () => api.get<{ providers: ProviderInfo[]; function_groups: FunctionGroup[] }>('/llm/providers'),
  getConfig: () => api.get<LLMConfigResponse>('/llm/config'),
  saveConfig: (config: LLMConfigResponse) => api.post<LLMConfigResponse>('/llm/config', config),
  test: (params: { provider: string; api_key?: string; base_url?: string; model?: string }) =>
    api.post<LLMTestResponse>('/llm/test', params),
}
```

- [ ] **Step 2: Commit API client changes**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat(frontend): add LLM API client methods"
```

---

## Task 5: Frontend LLM Config Card

**Files:**
- Modify: `frontend/src/pages/Home.tsx`

- [ ] **Step 1: Add state and imports for LLM config**

Update imports and add state:

```typescript
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText, GitBranch, Network, TrendingUp, Settings } from 'lucide-react'
import { graphApi, llmApi } from '../lib/api'
import LLMConfigModal from '../components/LLMConfigModal'

// ... inside Home component, add state:
const [llmStatus, setLlmStatus] = useState<string>('')
const [showLLMModal, setShowLLMModal] = useState(false)

// Add useEffect to load LLM status:
useEffect(() => {
  llmApi.getConfig().then(res => {
    const config = res.data
    if (config.providers && config.providers.length > 0) {
      const p = config.providers[0]
      setLlmStatus(`${p.provider} (${p.model || 'default'})`)
    } else {
      setLlmStatus('未配置')
    }
  }).catch(() => setLlmStatus('未配置'))
}, [])
```

- [ ] **Step 2: Add LLM config card to Quick Actions grid**

Replace the Quick Actions section:

```tsx
      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">快速操作</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/papers"
            className="flex items-center p-4 border rounded-lg hover:bg-gray-50"
          >
            <FileText className="h-6 w-6 text-blue-500 mr-3" />
            <div>
              <p className="font-medium">上传论文</p>
              <p className="text-sm text-gray-500">上传 PDF 并提取概念</p>
            </div>
          </Link>

          <Link
            to="/concepts"
            className="flex items-center p-4 border rounded-lg hover:bg-gray-50"
          >
            <GitBranch className="h-6 w-6 text-green-500 mr-3" />
            <div>
              <p className="font-medium">浏览概念</p>
              <p className="text-sm text-gray-500">查看概念层级树</p>
            </div>
          </Link>

          <button
            onClick={() => setShowLLMModal(true)}
            className="flex items-center p-4 border rounded-lg hover:bg-purple-50 text-left"
          >
            <Settings className="h-6 w-6 text-purple-500 mr-3" />
            <div>
              <p className="font-medium">LLM 配置</p>
              <p className="text-sm text-gray-500">{llmStatus || '配置 AI 服务商'}</p>
            </div>
          </button>
        </div>
      </div>

      {/* LLM Config Modal */}
      {showLLMModal && (
        <LLMConfigModal onClose={() => setShowLLMModal(false)} onSave={() => {
          setShowLLMModal(false)
          // Reload status
          llmApi.getConfig().then(res => {
            const config = res.data
            if (config.providers && config.providers.length > 0) {
              const p = config.providers[0]
              setLlmStatus(`${p.provider} (${p.model || 'default'})`)
            }
          })
        }} />
      )}
```

- [ ] **Step 3: Commit Home page changes**

```bash
git add frontend/src/pages/Home.tsx
git commit -m "feat(frontend): add LLM config card to homepage"
```

---

## Task 6: LLM Config Modal Component

**Files:**
- Create: `frontend/src/components/LLMConfigModal.tsx`

- [ ] **Step 1: Create the modal component**

```tsx
import { useEffect, useState } from 'react'
import { X, Check, Loader2 } from 'lucide-react'
import { llmApi } from '../lib/api'

interface Props {
  onClose: () => void
  onSave: () => void
}

interface ProviderConfig {
  function_group?: string
  provider: string
  api_key?: string
  base_url?: string
  model?: string
  is_active: boolean
}

export default function LLMConfigModal({ onClose, onSave }: Props) {
  const [mode, setMode] = useState<'single' | 'per_function'>('single')
  const [providers, setProviders] = useState<any[]>([])
  const [functionGroups, setFunctionGroups] = useState<any[]>([])
  const [configs, setConfigs] = useState<ProviderConfig[]>([{ provider: 'openai', is_active: true }])
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    llmApi.providers().then(res => {
      setProviders(res.data.providers)
      setFunctionGroups(res.data.function_groups)
    })
    llmApi.getConfig().then(res => {
      if (res.data.mode) setMode(res.data.mode as 'single' | 'per_function')
      if (res.data.providers?.length > 0) setConfigs(res.data.providers)
    })
  }, [])

  const currentProvider = providers.find(p => p.value === configs[0]?.provider)
  const requiresApiKey = currentProvider?.requires_api_key ?? true

  const updateConfig = (index: number, field: string, value: any) => {
    setConfigs(prev => {
      const updated = [...prev]
      updated[index] = { ...updated[index], [field]: value }
      return updated
    })
    setTestResult(null)
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const config = configs[0]
      const res = await llmApi.test({
        provider: config.provider,
        api_key: config.api_key,
        base_url: config.base_url,
        model: config.model,
      })
      setTestResult({ success: true, message: res.data.message })
    } catch (err: any) {
      setTestResult({ success: false, message: err.response?.data?.detail || '测试失败' })
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await llmApi.saveConfig({ mode, providers: configs })
      onSave()
    } catch (err) {
      alert('保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">LLM 服务配置</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Mode */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">配置模式</label>
            <div className="flex gap-2">
              <button
                onClick={() => setMode('single')}
                className={`flex-1 py-2 px-4 rounded-lg border text-sm font-medium ${
                  mode === 'single' ? 'border-purple-500 bg-purple-50 text-purple-700' : 'border-gray-200 text-gray-600'
                }`}
              >
                单一服务商
              </button>
              <button
                onClick={() => setMode('per_function')}
                className={`flex-1 py-2 px-4 rounded-lg border text-sm font-medium ${
                  mode === 'per_function' ? 'border-purple-500 bg-purple-50 text-purple-700' : 'border-gray-200 text-gray-600'
                }`}
              >
                按功能分配
              </button>
            </div>
          </div>

          {/* Provider Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">服务商</label>
            <select
              value={configs[0]?.provider || 'openai'}
              onChange={e => updateConfig(0, 'provider', e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm"
            >
              {providers.map(p => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>

          {/* Claude CLI notice */}
          {configs[0]?.provider === 'claude_cli' && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700">
              <Check className="inline h-4 w-4 mr-1" />
              Claude Code CLI 已自动检测到配置，无需输入 API Key
            </div>
          )}

          {/* API Key */}
          {requiresApiKey && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">API Key</label>
              <input
                type="password"
                value={configs[0]?.api_key || ''}
                onChange={e => updateConfig(0, 'api_key', e.target.value)}
                placeholder="sk-..."
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          )}

          {/* Base URL */}
          {requiresApiKey && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Base URL（可选）</label>
              <input
                type="text"
                value={configs[0]?.base_url || ''}
                onChange={e => updateConfig(0, 'base_url', e.target.value)}
                placeholder={currentProvider?.default_base_url || 'https://api.openai.com/v1'}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          )}

          {/* Model */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">模型</label>
            <input
              type="text"
              value={configs[0]?.model || ''}
              onChange={e => updateConfig(0, 'model', e.target.value)}
              placeholder="gpt-4, claude-sonnet-4-20250514, gemini-2.0-flash..."
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>

          {/* Test Result */}
          {testResult && (
            <div className={`rounded-lg p-3 text-sm ${testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
              {testResult.message}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-2 p-4 border-t bg-gray-50">
          <button
            onClick={handleTest}
            disabled={testing}
            className="flex-1 py-2 px-4 rounded-lg border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-50"
          >
            {testing ? <Loader2 className="inline h-4 w-4 animate-spin mr-1" /> : null}
            测试连接
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
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

- [ ] **Step 2: Commit modal component**

```bash
git add frontend/src/components/LLMConfigModal.tsx
git commit -m "feat(frontend): add LLM configuration modal component"
```

---

## Task 7: Integrate Database Config with LLM Extractor

**Files:**
- Modify: `backend/routes/papers.py`
- Modify: `backend/routes/concepts.py`

- [ ] **Step 1: Update `get_extractor()` in `papers.py` to use database config**

Replace the existing `get_extractor()` function:

```python
def get_extractor():
    global _extractor
    if _extractor is None:
        db = get_db()

        # Try database config first
        config = db.get_llm_config()
        if config and config.get('providers'):
            provider_config = None
            if config['mode'] == 'per_function':
                # For papers, use paper_parsing or default to first
                provider_config = db.get_llm_provider_for_function('paper_parsing')
                if not provider_config:
                    provider_config = config['providers'][0]
            else:
                provider_config = db.get_active_llm_provider()
                if not provider_config:
                    provider_config = config['providers'][0]

            if provider_config:
                return _create_client_from_config(provider_config)

        # Fallback to environment variables
        return _create_client_from_env()
    return _extractor


def _create_client_from_config(config: dict):
    """Create LLM client from database config"""
    provider = config.get('provider')
    api_key = config.get('api_key')
    base_url = config.get('base_url')
    model = config.get('model')

    if provider == 'claude_cli':
        return LLMConceptExtractor(ClaudeCLIClient())
    elif provider == 'anthropic':
        return LLMConceptExtractor(AnthropicClient(api_key, model=model or 'claude-sonnet-4-20250514', base_url=base_url))
    elif provider == 'google':
        return LLMConceptExtractor(GoogleClient(api_key))
    else:  # openai, dashscope, openrouter, minimax
        default_urls = {
            'dashscope': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            'openrouter': 'https://openrouter.ai/api/v1',
        }
        return LLMConceptExtractor(OpenAICompatibleClient(
            api_key,
            base_url=base_url or default_urls.get(provider),
            model=model
        ))


def _create_client_from_env():
    """Create LLM client from environment variables"""
    anthropic_token = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
    anthropic_base_url = os.getenv("ANTHROPIC_BASE_URL")
    anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    openai_key = os.getenv("OPENAI_API_KEY")
    openai_base_url = os.getenv("OPENAI_BASE_URL")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    google_key = os.getenv("GOOGLE_API_KEY")
    dashscope_key = os.getenv("DASHSCOPE_API_KEY")

    if not anthropic_token and not openai_key and not google_key and not dashscope_key:
        return None

    if anthropic_token:
        client = AnthropicClient(anthropic_token, model=anthropic_model, base_url=anthropic_base_url)
    elif openai_key:
        client = OpenAICompatibleClient(openai_key, base_url=openai_base_url, model=openai_model)
    elif google_key:
        client = GoogleClient(google_key)
    else:
        client = OpenAICompatibleClient(dashscope_key)
    return LLMConceptExtractor(client)
```

- [ ] **Step 2: Add imports to `papers.py`**

Add `ClaudeCLIClient` to imports:

```python
from openclaw.pdf_parser import PDFParser, LLMConceptExtractor, AnthropicClient, GoogleClient, OpenAICompatibleClient, ClaudeCLIClient
```

- [ ] **Step 3: Update `concepts.py` similarly**

Add the same `_create_client_from_config` helper and update `get_extractor_for_research` to use database config.

- [ ] **Step 4: Commit integration changes**

```bash
git add backend/routes/papers.py backend/routes/concepts.py
git commit -m "feat(backend): integrate database LLM config with extractor"
```

---

## Task 8: Test and Verify

- [ ] **Step 1: Restart backend server**

```bash
docker stop mkg && docker rm mkg
docker build -t meta-knowledge-graph:latest .
docker run -d -p 8088:8088 --name mkg meta-knowledge-graph:latest
```

- [ ] **Step 2: Test API endpoints**

```bash
curl http://localhost:8088/api/llm/providers
curl http://localhost:8088/api/llm/config
```

- [ ] **Step 3: Test frontend UI**

1. Open http://localhost:8088
2. Click "LLM 配置" card
3. Select provider, enter API key
4. Click "测试连接"
5. Click "保存配置"
6. Verify status updates on home page

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete LLM configuration feature"
git push origin main
```

---

## Summary

This plan implements:
1. Database schema for persisting LLM configurations
2. Backend API for CRUD operations and connection testing
3. Frontend modal UI with provider selection, API key input, test/save
4. Integration with existing LLM extraction code
5. Support for 7 providers including Claude Code CLI for testing