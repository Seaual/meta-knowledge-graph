# 概念去重前端功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为概念图谱页面添加去重功能 UI，支持用户扫描重复概念、查看 LLM 分析结果、勾选确认后执行合并。

**Architecture:** 在现有 Concepts.tsx 页面添加入口按钮，创建独立的 DedupPanel.tsx 侧边栏组件处理去重流程。通过 api.ts 新增 dedupApi 调用后端接口。

**Tech Stack:** React 18, TypeScript, TailwindCSS, lucide-react, axios

---

## 文件结构

```
frontend/src/
├── components/
│   └── DedupPanel.tsx      # 新建：去重侧边栏组件
├── lib/
│   └── api.ts              # 修改：新增 dedupApi
└── pages/
    └── Concepts.tsx        # 修改：添加入口按钮和侧边栏
```

---

### Task 1: 新增 dedupApi

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: 添加类型定义**

在 `frontend/src/lib/api.ts` 文件末尾添加类型定义：

```typescript
// Dedup API types
interface MergeSuggestion {
  id: string
  source: { id: string; text: string; paper_count: number }
  target: { id: string; text: string; paper_count: number }
  confidence: number
  rationale: string
}

interface DedupScanResponse {
  scan_id: string
  status: string
  candidates_found: number
  merge_suggestions: MergeSuggestion[]
}

interface ExecuteDetail {
  source: string
  target: string
  status: 'success' | 'failed'
  message?: string
}

interface DedupExecuteResponse {
  executed: number
  details: ExecuteDetail[]
}
```

- [ ] **Step 2: 添加 dedupApi**

在类型定义后添加 API 方法：

```typescript
export const dedupApi = {
  scan: () => api.post<DedupScanResponse>('/concepts/dedup/scan'),
  execute: (scanId: string, mergeIds: string[]) =>
    api.post<DedupExecuteResponse>('/concepts/dedup/execute', {
      scan_id: scanId,
      merge_ids: mergeIds,
    }),
}
```

- [ ] **Step 3: 验证编译**

```bash
cd D:/meta-knowledge-graph-main/frontend
npm run build
```

预期输出：编译成功，无错误

- [ ] **Step 4: 提交**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat(frontend): add dedupApi for deduplication feature"
```

---

### Task 2: 创建 DedupPanel 组件

**Files:**
- Create: `frontend/src/components/DedupPanel.tsx`

- [ ] **Step 1: 创建组件文件**

创建 `frontend/src/components/DedupPanel.tsx`：

```tsx
import { useState } from 'react'
import { X, RefreshCw, Check, AlertCircle, Merge } from 'lucide-react'
import { dedupApi } from '../lib/api'

// Types
interface MergeSuggestion {
  id: string
  source: { id: string; text: string; paper_count: number }
  target: { id: string; text: string; paper_count: number }
  confidence: number
  rationale: string
}

interface ExecuteDetail {
  source: string
  target: string
  status: 'success' | 'failed'
  message?: string
}

type PanelState = 'idle' | 'scanning' | 'review' | 'executing' | 'result'

interface DedupPanelProps {
  isOpen: boolean
  onClose: () => void
}

export default function DedupPanel({ isOpen, onClose }: DedupPanelProps) {
  const [panelState, setPanelState] = useState<PanelState>('idle')
  const [scanId, setScanId] = useState<string>('')
  const [suggestions, setSuggestions] = useState<MergeSuggestion[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [executeDetails, setExecuteDetails] = useState<ExecuteDetail[]>([])
  const [error, setError] = useState<string | null>(null)

  const handleScan = async () => {
    setPanelState('scanning')
    setError(null)
    try {
      const res = await dedupApi.scan()
      setScanId(res.data.scan_id)
      setSuggestions(res.data.merge_suggestions)
      setSelectedIds(new Set(res.data.merge_suggestions.map(s => s.id)))
      setPanelState('review')
    } catch (err: any) {
      setError(err.response?.data?.detail || '扫描失败')
      setPanelState('idle')
    }
  }

  const handleExecute = async () => {
    setPanelState('executing')
    setError(null)
    try {
      const res = await dedupApi.execute(scanId, Array.from(selectedIds))
      setExecuteDetails(res.data.details)
      setPanelState('result')
    } catch (err: any) {
      setError(err.response?.data?.detail || '执行失败')
      setPanelState('review')
    }
  }

  const toggleSelection = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleReset = () => {
    setPanelState('idle')
    setScanId('')
    setSuggestions([])
    setSelectedIds(new Set())
    setExecuteDetails([])
    setError(null)
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'bg-green-100 text-green-700'
    if (confidence >= 0.7) return 'bg-yellow-100 text-yellow-700'
    return 'bg-gray-100 text-gray-600'
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-white shadow-2xl z-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <Merge className="w-5 h-5 text-blue-500" />
          <h2 className="font-semibold text-lg">概念去重</h2>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg">
          <X className="w-5 h-5 text-gray-500" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Error */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Idle State */}
        {panelState === 'idle' && (
          <div className="text-center py-12">
            <Merge className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 mb-4">扫描知识图谱中的重复概念</p>
            <button
              onClick={handleScan}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              开始扫描
            </button>
          </div>
        )}

        {/* Scanning State */}
        {panelState === 'scanning' && (
          <div className="text-center py-12">
            <RefreshCw className="w-12 h-12 text-blue-500 mx-auto mb-4 animate-spin" />
            <p className="text-gray-600">正在扫描概念...</p>
            <p className="text-sm text-gray-400 mt-2">LLM 正在分析重复项</p>
          </div>
        )}

        {/* Review State */}
        {panelState === 'review' && (
          <div>
            <div className="mb-4">
              <p className="text-sm text-gray-500">
                发现 <span className="font-semibold text-gray-700">{suggestions.length}</span> 条合并建议
              </p>
            </div>

            {suggestions.length === 0 ? (
              <div className="text-center py-8">
                <Check className="w-12 h-12 text-green-500 mx-auto mb-4" />
                <p className="text-gray-600">未发现重复概念</p>
              </div>
            ) : (
              <div className="space-y-3">
                {suggestions.map(suggestion => (
                  <div
                    key={suggestion.id}
                    className="border rounded-lg p-3 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start gap-2">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(suggestion.id)}
                        onChange={() => toggleSelection(suggestion.id)}
                        className="mt-1 w-4 h-4 rounded border-gray-300"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-sm">
                            {suggestion.source.text}
                          </span>
                          <span className="text-gray-400">→</span>
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-sm">
                            {suggestion.target.text}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-xs ${getConfidenceColor(suggestion.confidence)}`}>
                            {Math.round(suggestion.confidence * 100)}%
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          论文数: {suggestion.source.paper_count} → {suggestion.target.paper_count}
                        </p>
                        <p className="text-xs text-gray-600 mt-2 bg-gray-50 p-2 rounded">
                          {suggestion.rationale}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Executing State */}
        {panelState === 'executing' && (
          <div className="text-center py-12">
            <RefreshCw className="w-12 h-12 text-blue-500 mx-auto mb-4 animate-spin" />
            <p className="text-gray-600">正在执行合并...</p>
          </div>
        )}

        {/* Result State */}
        {panelState === 'result' && (
          <div>
            <div className="mb-4">
              <p className="text-sm text-gray-500">
                已完成 <span className="font-semibold text-green-600">{executeDetails.filter(d => d.status === 'success').length}</span> 项合并
              </p>
            </div>

            <div className="space-y-2">
              {executeDetails.map((detail, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg ${
                    detail.status === 'success'
                      ? 'bg-green-50 border border-green-200'
                      : 'bg-red-50 border border-red-200'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {detail.status === 'success' ? (
                      <Check className="w-4 h-4 text-green-500" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-red-500" />
                    )}
                    <span className="text-sm">
                      {detail.source} → {detail.target}
                    </span>
                  </div>
                  {detail.message && (
                    <p className="text-xs text-red-600 mt-1 ml-6">{detail.message}</p>
                  )}
                </div>
              ))}
            </div>

            <button
              onClick={handleReset}
              className="w-full mt-4 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            >
              重新扫描
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      {panelState === 'review' && suggestions.length > 0 && (
        <div className="p-4 border-t">
          <button
            onClick={handleExecute}
            disabled={selectedIds.size === 0}
            className={`w-full py-2 rounded-lg transition-colors ${
              selectedIds.size > 0
                ? 'bg-blue-500 text-white hover:bg-blue-600'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            执行选中的合并 ({selectedIds.size})
          </button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 验证编译**

```bash
cd D:/meta-knowledge-graph-main/frontend
npm run build
```

预期输出：编译成功

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/DedupPanel.tsx
git commit -m "feat(frontend): add DedupPanel component for deduplication"
```

---

### Task 3: 集成到 Concepts 页面

**Files:**
- Modify: `frontend/src/pages/Concepts.tsx`

- [ ] **Step 1: 添加 import 和 state**

在 `Concepts.tsx` 文件顶部添加 import：

```tsx
import DedupPanel from '../components/DedupPanel'
```

在 `GraphCanvas` 组件内添加 state（在其他 useState 附近）：

```tsx
const [dedupOpen, setDedupOpen] = useState(false)
```

- [ ] **Step 2: 添加去重按钮**

找到 `Panel position="top-right"` 部分，在布局切换按钮后添加去重按钮：

```tsx
<button
  onClick={() => setDedupOpen(true)}
  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100"
>
  <Merge className="w-4 h-4" />
  去重扫描
</button>
```

- [ ] **Step 3: 添加 DedupPanel 组件**

在 `GraphCanvas` 组件返回的 JSX 末尾（`</div>` 之前）添加：

```tsx
<DedupPanel isOpen={dedupOpen} onClose={() => setDedupOpen(false)} />
```

- [ ] **Step 4: 添加 Merge 图标 import**

确保在 lucide-react import 中添加 `Merge`：

```tsx
import { Search, FileText, X, ArrowLeft, BookOpen, GitBranch, Zap, Merge } from 'lucide-react'
```

- [ ] **Step 5: 验证编译**

```bash
cd D:/meta-knowledge-graph-main/frontend
npm run build
```

预期输出：编译成功

- [ ] **Step 6: 提交**

```bash
git add frontend/src/pages/Concepts.tsx
git commit -m "feat(frontend): integrate DedupPanel into Concepts page"
```

---

### Task 4: 集成测试

**Files:**
- Test: 前端功能测试

- [ ] **Step 1: 启动后端服务**

```bash
cd D:/meta-knowledge-graph-main
venv\Scripts\activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8088
```

- [ ] **Step 2: 启动前端服务**

新终端：

```bash
cd D:/meta-knowledge-graph-main/frontend
npm run dev
```

- [ ] **Step 3: 测试功能**

1. 访问 http://localhost:5173/concepts
2. 点击右上角"去重扫描"按钮
3. 确认侧边栏打开，显示"开始扫描"按钮
4. 点击"开始扫描"，确认进入扫描状态
5. 扫描完成后，确认显示合并建议列表
6. 勾选/取消勾选建议
7. 点击"执行选中的合并"
8. 确认显示执行结果

- [ ] **Step 4: 最终提交**

```bash
git add -A
git commit -m "feat(frontend): complete deduplication UI

- Add DedupPanel component with scan/review/execute flow
- Add dedupApi for backend integration
- Integrate into Concepts page with sidebar button"
```

---

## 注意事项

1. **LLM 配置**：确保后端已配置 API Key（ANTHROPIC_API_KEY / GOOGLE_API_KEY / DASHSCOPE_API_KEY）

2. **样式一致性**：使用 TailwindCSS，与现有组件风格保持一致

3. **错误处理**：所有 API 调用都有 try-catch，显示用户友好的错误信息