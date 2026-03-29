# 图谱搜索与过滤实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户能够快速找到特定概念、按 category 过滤节点、点击定位到目标节点。

**Architecture:**
1. 新建 FilterPanel 组件，包含搜索框和 category 过滤器
2. 在 ConceptsGraph 中集成面板，实现搜索高亮和节点定位
3. 使用 ForceGraph API 实现缩放和居中

**Tech Stack:** React, TypeScript, ForceGraph, Tailwind CSS

---

## File Structure

| 文件 | 职责 |
|------|------|
| `frontend/src/components/FilterPanel.tsx` | 筛选面板组件（搜索框 + category 过滤器） |
| `frontend/src/pages/ConceptsGraph.tsx` | 集成面板、搜索高亮、节点定位逻辑 |

---

### Task 1: 创建 FilterPanel 组件

**Files:**
- Create: `frontend/src/components/FilterPanel.tsx`

- [ ] **Step 1: 创建 FilterPanel.tsx**

```tsx
import { useState, useEffect, useRef } from 'react'
import { X, Search, RotateCcw } from 'lucide-react'

interface Concept {
  id: string
  text: string
  category: string | null
  paper_count: number
}

interface Props {
  concepts: Concept[]
  onClose: () => void
  onSearch: (query: string, results: Concept[]) => void
  onCategoryChange: (categories: string[]) => void
  onFocusNode: (nodeId: string) => void
}

const CATEGORIES = [
  { id: 'field', label: '领域', color: '#FF6B6B' },
  { id: 'direction', label: '方向', color: '#4ECDC4' },
  { id: 'subdirection', label: '子方向', color: '#45B7D1' },
  { id: 'task', label: '任务', color: '#96CEB4' },
  { id: 'method', label: '方法', color: '#FFA726' },
  { id: 'technique', label: '技术', color: '#FFD93D' },
]

export default function FilterPanel({
  concepts,
  onClose,
  onSearch,
  onCategoryChange,
  onFocusNode
}: Props) {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Concept[]>([])
  const [showResults, setShowResults] = useState(false)
  const [selectedCategories, setSelectedCategories] = useState<string[]>(
    CATEGORIES.map(c => c.id)
  )
  const [conceptCounts, setConceptCounts] = useState<Record<string, number>>({})
  const searchInputRef = useRef<HTMLInputElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)

  // 计算每个 category 的概念数量
  useEffect(() => {
    const counts: Record<string, number> = {}
    concepts.forEach(c => {
      if (c.category) {
        counts[c.category] = (counts[c.category] || 0) + 1
      }
    })
    setConceptCounts(counts)
  }, [concepts])

  // 搜索逻辑
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      onSearch('', [])
      return
    }

    const query = searchQuery.toLowerCase()
    const results = concepts
      .filter(c => c.text.toLowerCase().includes(query))
      .slice(0, 10)

    setSearchResults(results)
    onSearch(searchQuery, results)
  }, [searchQuery, concepts, onSearch])

  // Category 变化通知
  useEffect(() => {
    onCategoryChange(selectedCategories)
  }, [selectedCategories, onCategoryChange])

  // 聚焦搜索框
  useEffect(() => {
    searchInputRef.current?.focus()
  }, [])

  const toggleCategory = (categoryId: string) => {
    setSelectedCategories(prev =>
      prev.includes(categoryId)
        ? prev.filter(c => c !== categoryId)
        : [...prev, categoryId]
    )
  }

  const handleReset = () => {
    setSearchQuery('')
    setSearchResults([])
    setSelectedCategories(CATEGORIES.map(c => c.id))
  }

  const handleResultClick = (concept: Concept) => {
    setShowResults(false)
    onFocusNode(concept.id)
  }

  return (
    <div className="absolute top-4 right-4 z-20 w-72 bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-brand-gradient border-b border-brand">
        <h3 className="font-semibold text-brand-700">筛选</h3>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-700 transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-gray-100">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onFocus={() => setShowResults(true)}
            placeholder="搜索概念..."
            className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />
        </div>

        {/* Search Results */}
        {showResults && searchResults.length > 0 && (
          <div
            ref={resultsRef}
            className="absolute left-4 right-4 mt-2 bg-white border border-gray-200 rounded-xl shadow-lg max-h-64 overflow-y-auto z-30"
          >
            {searchResults.map(concept => {
              const category = CATEGORIES.find(c => c.id === concept.category)
              return (
                <button
                  key={concept.id}
                  onClick={() => handleResultClick(concept)}
                  className="w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center justify-between border-b border-gray-100 last:border-b-0"
                >
                  <span className="text-sm text-gray-700">{concept.text}</span>
                  {category && (
                    <span
                      className="text-xs px-2 py-0.5 rounded-full text-white"
                      style={{ backgroundColor: category.color }}
                    >
                      {category.label}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* Category Filters */}
      <div className="p-4">
        <div className="text-xs font-medium text-gray-500 mb-3">Category 过滤</div>
        <div className="space-y-2">
          {CATEGORIES.map(category => (
            <label
              key={category.id}
              className="flex items-center gap-3 cursor-pointer hover:bg-gray-50 p-2 rounded-lg transition-colors"
            >
              <input
                type="checkbox"
                checked={selectedCategories.includes(category.id)}
                onChange={() => toggleCategory(category.id)}
                className="w-4 h-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              />
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: category.color }}
              />
              <span className="text-sm text-gray-700 flex-1">{category.label}</span>
              <span className="text-xs text-gray-400">
                {conceptCounts[category.id] || 0}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Reset Button */}
      <div className="px-4 pb-4">
        <button
          onClick={handleReset}
          className="w-full py-2.5 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-50 rounded-xl transition-colors flex items-center justify-center gap-2"
        >
          <RotateCcw className="h-4 w-4" />
          重置全部
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/FilterPanel.tsx
git commit -m "feat(frontend): add FilterPanel component for graph search and filter"
```

---

### Task 2: 在 ConceptsGraph 中集成筛选状态

**Files:**
- Modify: `frontend/src/pages/ConceptsGraph.tsx`

- [ ] **Step 1: 添加导入语句**

在文件顶部添加：

```tsx
import FilterPanel from '../components/FilterPanel'
import { Search, RotateCcw } from 'lucide-react'
```

- [ ] **Step 2: 添加筛选相关状态**

在 `const [graphLinks, setGraphLinks] = useState...` 之后添加：

```tsx
  // Filter panel state
  const [filterPanelOpen, setFilterPanelOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Concept[]>([])
  const [selectedCategories, setSelectedCategories] = useState<string[]>([
    'field', 'direction', 'subdirection', 'task', 'method', 'technique'
  ])
  const [highlightedNodeId, setHighlightedNodeId] = useState<string | null>(null)
```

- [ ] **Step 3: 添加搜索和过滤处理函数**

在状态声明之后添加：

```tsx
  // Filter handlers
  const handleSearch = useCallback((query: string, results: Concept[]) => {
    setSearchQuery(query)
    setSearchResults(results)
  }, [])

  const handleCategoryChange = useCallback((categories: string[]) => {
    setSelectedCategories(categories)
  }, [])

  const handleFocusNode = useCallback((nodeId: string) => {
    const node = graphNodes.find(n => n.id === nodeId)
    if (node && graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 1000)
      graphRef.current.zoom(2, 1000)
      setHighlightedNodeId(nodeId)
      setTimeout(() => setHighlightedNodeId(null), 2000)
    }
  }, [graphNodes])
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ConceptsGraph.tsx
git commit -m "feat(frontend): add filter state and handlers to ConceptsGraph"
```

---

### Task 3: 修改节点渲染逻辑实现高亮和过滤

**Files:**
- Modify: `frontend/src/pages/ConceptsGraph.tsx`

- [ ] **Step 1: 修改节点颜色函数，添加透明度逻辑**

找到 `nodeCanvasObject` 函数定义的位置，在其中添加透明度计算。

在现有的颜色计算之后，添加透明度逻辑：

```tsx
// 在 nodeCanvasObject 函数内部，绘制节点之前添加：

    // Calculate opacity based on search and category filter
    let opacity = 1
    if (searchQuery) {
      const matchesSearch = node.name.toLowerCase().includes(searchQuery.toLowerCase())
      opacity = matchesSearch ? 1 : 0.2
    } else if (node.category && !selectedCategories.includes(node.category)) {
      opacity = 0.15
    }

    // Highlighted node gets special treatment
    if (highlightedNodeId === node.id) {
      opacity = 1
    }
```

- [ ] **Step 2: 应用透明度到 Canvas 绘制**

修改绘制节点的代码，在 `ctx.fillStyle` 设置时应用透明度：

```tsx
// 修改类似这样的代码：
ctx.fillStyle = color

// 改为：
ctx.globalAlpha = opacity
ctx.fillStyle = color
// 绘制完成后恢复
ctx.globalAlpha = 1
```

- [ ] **Step 3: 添加高亮节点发光效果**

在节点绘制逻辑中添加：

```tsx
    // Highlighted node glow effect
    if (highlightedNodeId === node.id) {
      ctx.beginPath()
      ctx.arc(node.x!, node.y!, size + 8, 0, 2 * Math.PI)
      ctx.fillStyle = 'rgba(255, 200, 0, 0.4)'
      ctx.fill()
    }
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ConceptsGraph.tsx
git commit -m "feat(frontend): implement search highlight and category filter opacity"
```

---

### Task 4: 添加筛选按钮和渲染 FilterPanel

**Files:**
- Modify: `frontend/src/pages/ConceptsGraph.tsx`

- [ ] **Step 1: 在右上角工具栏添加筛选按钮**

找到 `{/* Action Buttons */}` 部分，在文件夹选择器之前添加筛选按钮：

```tsx
      {/* Action Buttons */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        {/* Filter Button */}
        <button
          onClick={() => setFilterPanelOpen(!filterPanelOpen)}
          className={`flex items-center gap-2 px-4 py-2.5 backdrop-blur rounded-xl shadow-brand text-sm font-medium transition-all border ${
            filterPanelOpen
              ? 'bg-brand-fill text-brand-700 border-brand'
              : 'bg-brand-gradient text-brand-600 hover:shadow-brand-lg border-brand'
          }`}
        >
          <Search className="h-4 w-4" />
          筛选
        </button>
        {/* Folder Selector - existing code */}
        <div className="relative">
          ...
```

- [ ] **Step 2: 在组件末尾渲染 FilterPanel**

在 `{/* Paper Detail Panel */}` 之前添加：

```tsx
      {/* Filter Panel */}
      {filterPanelOpen && (
        <FilterPanel
          concepts={concepts}
          onClose={() => setFilterPanelOpen(false)}
          onSearch={handleSearch}
          onCategoryChange={handleCategoryChange}
          onFocusNode={handleFocusNode}
        />
      )}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ConceptsGraph.tsx
git commit -m "feat(frontend): integrate FilterPanel with search and focus functionality"
```

---

### Task 5: 测试验证

**Files:**
- Test: Manual testing

- [ ] **Step 1: 构建前端验证无编译错误**

```bash
cd frontend && npm run build
```

Expected: Build successful with no TypeScript errors

- [ ] **Step 2: 启动开发服务器测试功能**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: 手动测试清单**

1. 打开图谱页面，点击右上角"筛选"按钮
2. 验证面板从右侧滑出
3. 输入搜索词，验证匹配节点高亮，其他节点变淡
4. 验证下拉列表显示匹配结果
5. 点击某个结果，验证图谱定位到该节点
6. 取消勾选某个 category，验证对应节点变淡
7. 点击"重置全部"，验证恢复默认状态
8. 点击关闭按钮，验证面板收起

- [ ] **Step 4: 最终 commit**

```bash
git add -A
git commit -m "feat(frontend): complete graph search and filter feature"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | 创建 FilterPanel 组件 | `frontend/src/components/FilterPanel.tsx` |
| 2 | 添加筛选状态和处理函数 | `frontend/src/pages/ConceptsGraph.tsx` |
| 3 | 实现节点高亮和过滤透明度 | `frontend/src/pages/ConceptsGraph.tsx` |
| 4 | 集成筛选按钮和面板渲染 | `frontend/src/pages/ConceptsGraph.tsx` |
| 5 | 测试验证 | Manual testing |