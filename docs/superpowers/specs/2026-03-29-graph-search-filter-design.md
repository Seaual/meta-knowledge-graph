# 图谱搜索与过滤设计

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-step. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户能够快速找到特定概念、按 category 过滤节点、点击定位到目标节点。

**Architecture:**
1. 右侧可折叠筛选面板，包含搜索框和 category 过滤器
2. 搜索时实时高亮匹配节点 + 下拉选择列表
3. 点击结果定位到节点

**Tech Stack:** React, TypeScript, D3.js/ForceGraph

---

## 1. UI 布局

### 1.1 筛选按钮

位置：右上角工具栏，在导出按钮左侧

```
[筛选] [文件夹 ▼] [导出 ▼]
```

点击筛选按钮 → 右侧面板滑出

### 1.2 右侧筛选面板

```
┌─────────────────────────┐
│ 筛选               [×] │
├─────────────────────────┤
│ 🔍 [搜索概念...]        │
│                         │
│ ┌─────────────────────┐ │
│ │ Transformer (method)│ │
│ │ Self-Attention      │ │
│ │ ...                 │ │
│ └─────────────────────┘ │
│                         │
│ ── Category 过滤 ──     │
│ ☑ field      (2)        │
│ ☑ direction  (5)        │
│ ☑ subdirection (8)      │
│ ☐ task      (12)        │
│ ☑ method    (15)        │
│ ☑ technique (6)         │
│                         │
│ [重置全部]              │
└─────────────────────────┘
```

**宽度：** 280px
**动画：** 从右侧滑入/滑出

---

## 2. 搜索功能

### 2.1 实时搜索

**输入时：**
- 节流处理（300ms）
- 搜索所有概念节点的 `name` 字段
- 不区分大小写
- 支持中文和英文

### 2.2 高亮匹配节点

**视觉效果：**
- 匹配节点：正常颜色 + 发光效果
- 非匹配节点：降低透明度（opacity: 0.2）
- 匹配数量显示在搜索框下方

### 2.3 下拉结果列表

**显示：**
- 最多 10 个结果
- 每个结果：概念名称 + category 彩色标签
- 键盘支持：↑↓ 选择，Enter 确认

**点击结果：**
- 关闭下拉列表
- 图谱缩放到该节点（zoom = 2x）
- 节点居中显示
- 节点闪烁高亮效果（2秒）

---

## 3. Category 过滤

### 3.1 过滤器

**交互：**
- 6 个复选框对应 6 个 category
- 默认全部勾选
- 取消勾选后，对应 category 的节点变淡（opacity: 0.15）
- 显示每个 category 的节点数量

### 3.2 颜色标识

| Category | 颜色 |
|----------|------|
| field | #FF6B6B |
| direction | #4ECDC4 |
| subdirection | #45B7D1 |
| task | #96CEB4 |
| method | #FFA726 |
| technique | #FFD93D |

### 3.3 重置按钮

点击"重置全部"：
- 清空搜索框
- 全部 category 恢复勾选
- 所有节点恢复正常显示

---

## 4. 技术实现

### 4.1 状态管理

```typescript
// 筛选面板状态
const [filterPanelOpen, setFilterPanelOpen] = useState(false)

// 搜索状态
const [searchQuery, setSearchQuery] = useState('')
const [searchResults, setSearchResults] = useState<Concept[]>([])
const [highlightedNodeId, setHighlightedNodeId] = useState<string | null>(null)

// Category 过滤状态
const [selectedCategories, setSelectedCategories] = useState<string[]>([
  'field', 'direction', 'subdirection', 'task', 'method', 'technique'
])
```

### 4.2 节点过滤逻辑

```typescript
// 计算节点透明度
const getNodeOpacity = (node: GraphNode): number => {
  // 搜索过滤优先
  if (searchQuery && !node.name.toLowerCase().includes(searchQuery.toLowerCase())) {
    return 0.2
  }

  // Category 过滤
  if (node.category && !selectedCategories.includes(node.category)) {
    return 0.15
  }

  return 1
}
```

### 4.3 定位到节点

```typescript
const focusNode = (nodeId: string) => {
  const node = graphNodes.find(n => n.id === nodeId)
  if (node && graphRef.current) {
    graphRef.current.centerAt(node.x, node.y, 1000) // 1s 动画
    graphRef.current.zoom(2, 1000)
    setHighlightedNodeId(nodeId)
    setTimeout(() => setHighlightedNodeId(null), 2000)
  }
}
```

---

## 5. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/components/FilterPanel.tsx` | 新增 | 筛选面板组件 |
| `frontend/src/pages/ConceptsGraph.tsx` | 修改 | 集成筛选面板、搜索高亮、定位功能 |

---

## 6. 验收标准

1. ✅ 点击筛选按钮，右侧面板滑出
2. ✅ 输入搜索词，匹配节点高亮，其他节点变淡
3. ✅ 下拉列表显示匹配结果，最多 10 个
4. ✅ 点击结果，图谱定位到该节点
5. ✅ 取消勾选 category，对应节点变淡
6. ✅ 点击重置，恢复默认状态
7. ✅ 面板可折叠，不影响图谱正常使用