# 概念去重前端设计

## 概述

为概念图谱页面添加去重功能 UI，支持用户扫描重复概念、查看 LLM 分析结果、勾选确认后执行合并。

## 需求

- **入口位置**：概念页面右上角按钮
- **交互方式**：点击按钮 → 弹出侧边栏 → 列表勾选 → 批量执行
- **信息展示**：显示源概念、目标概念、置信度、论文数、合并理由
- **结果反馈**：每条合并单独显示成功/失败状态

## 组件结构

```
frontend/src/
├── components/
│   └── DedupPanel.tsx      # 去重侧边栏组件
└── lib/
    └── api.ts              # 新增 dedupApi
```

## 组件设计

### DedupPanel 组件

**Props:**
```typescript
interface DedupPanelProps {
  isOpen: boolean
  onClose: () => void
}
```

**State:**
```typescript
type PanelState = 'idle' | 'scanning' | 'review' | 'executing' | 'result'

// 扫描结果
interface MergeSuggestion {
  id: string
  source: { id: string; text: string; paper_count: number }
  target: { id: string; text: string; paper_count: number }
  confidence: number
  rationale: string
}

// 执行结果
interface ExecuteDetail {
  source: string
  target: string
  status: 'success' | 'failed'
  message?: string
}
```

**UI 状态流程：**

1. **idle** - 显示"开始扫描"按钮
2. **scanning** - 显示加载动画和进度文字
3. **review** - 显示合并建议列表，每项可勾选
4. **executing** - 显示"执行中..."加载状态
5. **result** - 显示执行结果列表

### 合并建议卡片

```tsx
function MergeSuggestionCard({
  suggestion,
  selected,
  onToggle
}: {
  suggestion: MergeSuggestion
  selected: boolean
  onToggle: () => void
}) {
  return (
    <div className="border rounded-lg p-3">
      <div className="flex items-center gap-2">
        <input type="checkbox" checked={selected} onChange={onToggle} />
        <span className="badge-red">{suggestion.source.text}</span>
        <span>→</span>
        <span className="badge-green">{suggestion.target.text}</span>
      </div>
      <div className="text-sm text-gray-500 mt-1">
        置信度: {suggestion.confidence * 100}% · 论文数: {suggestion.source.paper_count} → {suggestion.target.paper_count}
      </div>
      <div className="text-sm text-gray-600 mt-1 bg-gray-50 p-2 rounded">
        {suggestion.rationale}
      </div>
    </div>
  )
}
```

## API 集成

在 `api.ts` 新增：

```typescript
export const dedupApi = {
  scan: () => api.post<DedupScanResponse>('/concepts/dedup/scan'),
  execute: (scanId: string, mergeIds: string[]) =>
    api.post<DedupExecuteResponse>('/concepts/dedup/execute', {
      scan_id: scanId,
      merge_ids: mergeIds,
    }),
}

interface DedupScanResponse {
  scan_id: string
  status: string
  candidates_found: number
  merge_suggestions: MergeSuggestion[]
}

interface DedupExecuteResponse {
  executed: number
  details: ExecuteDetail[]
}
```

## 交互流程

```
用户点击"去重扫描"
    ↓
调用 dedupApi.scan()
    ↓
显示 scanning 状态
    ↓
收到响应，切换到 review 状态
    ↓
用户勾选想要的合并
    ↓
点击"执行选中"按钮
    ↓
调用 dedupApi.execute(scanId, selectedIds)
    ↓
显示 executing 状态
    ↓
收到响应，切换到 result 状态
    ↓
显示每条合并的成功/失败状态
```

## 错误处理

| 场景 | 处理 |
|------|------|
| LLM 未配置 | 显示错误提示："请先配置 API Key" |
| 扫描无结果 | 显示空状态："未发现重复概念" |
| 执行失败 | 在结果列表中显示失败原因 |
| 网络错误 | 显示错误 toast，保持在当前状态 |

## 样式规范

- 侧边栏宽度：384px (w-96)
- 卡片圆角：8px (rounded-lg)
- 成功状态：绿色背景 (#DCFCE7)
- 失败状态：红色背景 (#FEE2E2)
- 置信度标签颜色：
  - 高 (≥90%): 绿色
  - 中 (70-90%): 黄色
  - 低 (<70%): 灰色

## 入口按钮位置

在 `Concepts.tsx` 的右上角面板区域添加按钮：

```tsx
<Panel position="top-right" className="!m-2">
  <div className="bg-white/90 backdrop-blur rounded-xl shadow-lg p-1 flex gap-1">
    {/* 现有的布局切换按钮 */}
    ...
    {/* 新增去重按钮 */}
    <button
      onClick={() => setDedupOpen(true)}
      className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100"
    >
      <Merge className="w-4 h-4" />
      去重扫描
    </button>
  </div>
</Panel>
```

## 文件变更清单

| 文件 | 操作 |
|------|------|
| `frontend/src/components/DedupPanel.tsx` | 新建 |
| `frontend/src/lib/api.ts` | 修改（新增 dedupApi） |
| `frontend/src/pages/Concepts.tsx` | 修改（添加入口按钮和侧边栏） |