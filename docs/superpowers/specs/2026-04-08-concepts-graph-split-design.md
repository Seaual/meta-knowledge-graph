# ConceptsGraph.tsx 页面拆分设计

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:writing-plans to create implementation plan after spec approval.

**Goal:** 将 `pages/ConceptsGraph.tsx` (1612行) 拆分为职责清晰的模块，提高可维护性。

**Architecture:** 按职责拆分 - types、constants、hooks 分离，组件使用自定义 hook。

**Tech Stack:** React, TypeScript, ForceGraph

---

## 当前问题

`frontend/src/pages/ConceptsGraph.tsx` 包含 1612 行：
- 类型定义 (~90行)
- 状态管理 (~20个 useState)
- 回调函数 (~20个 useCallback)
- 数据加载 (useEffect)
- 图渲染 (ForceGraph)
- UI渲染 (JSX)

问题：
- 单文件过大，难以维护
- 类型与逻辑混杂
- 难以单独测试

---

## 目标结构

```
frontend/src/pages/ConceptsGraph/
├── index.tsx           # 主组件（精简版，~400行）
├── types.ts            # 类型定义（~50行）
├── constants.ts        # 颜色常量等（~20行）
└── hooks/
    └── useGraph.ts     # 图状态和操作（~300行）
```

---

## 模块详细设计

### types.ts

```typescript
// frontend/src/pages/ConceptsGraph/types.ts

export interface Concept {
  id: string
  text: string
  text_en?: string
  category: string | null | undefined
  paper_count: number
  parents?: Concept[]
  children?: Concept[]
  papers?: { doi: string; title: string }[]
}

export interface Paper {
  doi: string
  title: string
  authors?: string[]
  keywords?: string[]
  contributions?: string[]
  abstract: string | null
  status: string
  s2_doi?: string
  venue?: string
  year?: number
  citation_count?: number
  tldr?: string
  s2_fields_of_study?: string[]
}

export interface GraphEdge {
  source: string
  target: string
}

export type NodeType = 'concept' | 'paper' | 'center'

export interface GraphNode {
  id: string
  name: string
  name_en?: string
  type: NodeType
  category?: string
  paperCount?: number
  depth?: number
  authors?: string[]
  keywords?: string[]
  abstract?: string | null
  doi?: string
  x?: number
  y?: number
  vx?: number
  vy?: number
  fx?: number
  fy?: number
}

export interface ResearchPoint {
  title: string
  hypothesis: string
  description: string
  discovery_method: 'gap_filling' | 'leaf_extension' | 'bottleneck' | 'transfer'
  rationale: string
  related_concepts: string[]
  difficulty: 'low' | 'medium' | 'high'
  difficulty_reason: string
  novelty: 'incremental' | 'moderate' | 'high'
  potential_impact: 'niche' | 'broad' | 'transformative'
}

export interface ResearchPointsResponse {
  concept_id: string
  concept_name: string
  research_points: ResearchPoint[]
  analysis_context: {
    concept: { id: string; name: string; category?: string }
    ancestors: { id: string; name: string; category?: string }[]
    descendants: { id: string; name: string; category?: string; depth?: number }[]
    edge_nodes: { id: string; name: string; category?: string }[]
    related_papers: { title: string; keywords?: string[] }[]
  }
}
```

### constants.ts

```typescript
// frontend/src/pages/ConceptsGraph/constants.ts

// Category colors - Academic Warm Palette
export const CATEGORY_COLORS: Record<string, string> = {
  field: '#6b4423',        // sepia
  direction: '#b8860b',    // amber
  subdirection: '#9a6b3c', // copper
  task: '#4a6b8a',         // slate blue
  method: '#c2410c',       // terracotta
  technique: '#2d5a27',    // forest green
  dataset: '#5c4d7d',      // purple
  finding: '#d4a012',      // gold
}

export const PAPER_COLOR = '#4a6b8a'
export const CENTER_COLOR = '#d4a012'

export const DEFAULT_CATEGORIES = [
  'field', 'direction', 'subdirection', 'task', 'method', 'technique', 'dataset', 'finding'
]
```

### hooks/useGraph.ts

```typescript
// frontend/src/pages/ConceptsGraph/hooks/useGraph.ts

import { useState, useEffect, useCallback } from 'react'
import { conceptsApi, graphApi, papersApi, foldersApi } from '@/lib/api'
import { useAgentStore } from '@/stores/agentStore'
import type { Concept, Paper, GraphNode, GraphEdge, ResearchPointsResponse } from '../types'

interface UseGraphReturn {
  // Data
  loading: boolean
  concepts: Concept[]
  edges: GraphEdge[]
  graphNodes: GraphNode[]
  graphLinks: { source: string; target: string }[]
  folders: { id: string; name: string }[]
  
  // View state
  viewMode: 'all' | 'concept'
  selectedConcept: Concept | null
  selectedPaper: Paper | null
  activeFolder: string
  
  // Research points
  researchPoints: ResearchPointsResponse | null
  loadingResearchPoints: boolean
  
  // Actions
  handleConceptClick: (node: GraphNode) => Promise<void>
  handlePaperClick: (node: GraphNode) => Promise<void>
  handleViewPapers: () => void
  handleBack: () => void
  handleDiscoverResearchPoints: () => Promise<void>
  setActiveFolder: (folder: string) => void
  loadFolders: () => void
  
  // Graph methods
  getNodeDepth: (nodeId: string, parentMap: Map<string, string>) => number
}

export function useGraph(): UseGraphReturn {
  // ... 所有状态和逻辑移到这里
}
```

### index.tsx

主组件保持 UI 渲染逻辑，使用 useGraph hook：

```typescript
// frontend/src/pages/ConceptsGraph/index.tsx

import { useRef, useState, useCallback } from 'react'
import ForceGraph from 'force-graph'
import { useGraph } from './hooks/useGraph'
import { CATEGORY_COLORS, PAPER_COLOR, CENTER_COLOR } from './constants'
import type { GraphNode } from './types'
// ... 其他 imports

export default function ConceptsGraph() {
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<any>(null)
  
  // 使用 hook
  const {
    loading, concepts, graphNodes, graphLinks,
    selectedConcept, selectedPaper, viewMode,
    handleConceptClick, handlePaperClick, handleViewPapers,
    // ... 其他
  } = useGraph()
  
  // 本地 UI 状态
  const [dedupOpen, setDedupOpen] = useState(false)
  const [filterPanelOpen, setFilterPanelOpen] = useState(false)
  // ...
  
  // ForceGraph 渲染配置
  // JSX 返回
}
```

---

## 向后兼容

路由无需修改：
```typescript
// 仍然有效
import ConceptsGraph from '@/pages/ConceptsGraph'
```

---

## 实现步骤

1. 创建 `pages/ConceptsGraph/` 目录
2. 创建 `types.ts` - 提取类型定义
3. 创建 `constants.ts` - 提取常量
4. 创建 `hooks/useGraph.ts` - 提取状态和逻辑
5. 创建 `index.tsx` - 精简主组件
6. 删除旧文件 `pages/ConceptsGraph.tsx`
7. 验证功能正常
8. 提交

---

## 预期结果

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| 最大文件行数 | 1612 | ~400 |
| 文件数 | 1 | 4 |
| 类型可复用 | ❌ | ✅ |
| Hook 可测试 | ❌ | ✅ |
| 向后兼容 | N/A | ✅ |