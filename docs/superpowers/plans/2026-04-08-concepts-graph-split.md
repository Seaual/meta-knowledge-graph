# ConceptsGraph 页面拆分实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `pages/ConceptsGraph.tsx` (1612行) 拆分为职责清晰的模块。

**Architecture:** 按职责拆分 - types、constants、hooks 分离，组件使用自定义 hook。

**Tech Stack:** React, TypeScript, ForceGraph

---

## 文件结构

```
frontend/src/pages/ConceptsGraph/
├── index.tsx           # 主组件（~400行）
├── types.ts            # 类型定义（~50行）
├── constants.ts        # 颜色常量等（~20行）
└── hooks/
    └── useGraph.ts     # 图状态和操作（~300行）
```

---

## Task 1: 创建目录和 types.ts

**Files:**
- Create: `frontend/src/pages/ConceptsGraph/types.ts`

- [ ] **Step 1: 创建 types.ts**

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

- [ ] **Step 2: 提交**

```bash
git add frontend/src/pages/ConceptsGraph/types.ts
git commit -m "feat(frontend): add ConceptsGraph types module"
```

---

## Task 2: 创建 constants.ts

**Files:**
- Create: `frontend/src/pages/ConceptsGraph/constants.ts`

- [ ] **Step 1: 创建 constants.ts**

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

// Category-based sizes (decreasing by hierarchy level)
export const CATEGORY_SIZES: Record<string, number> = {
  field: 16,        // largest
  direction: 14,
  subdirection: 12,
  dataset: 12,      // medium (same as subdirection)
  finding: 12,      // medium (same as subdirection)
  task: 10,
  method: 8,
  technique: 6,     // smallest
}

// Category-based collision radius
export const CATEGORY_RADII: Record<string, number> = {
  field: 20,
  direction: 18,
  subdirection: 16,
  dataset: 16,
  finding: 16,
  task: 14,
  method: 12,
  technique: 10,
}

export const DEFAULT_CATEGORIES = [
  'field', 'direction', 'subdirection', 'task', 'method', 'technique', 'dataset', 'finding'
]
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/pages/ConceptsGraph/constants.ts
git commit -m "feat(frontend): add ConceptsGraph constants module"
```

---

## Task 3: 创建 useGraph hook

**Files:**
- Create: `frontend/src/pages/ConceptsGraph/hooks/useGraph.ts`

- [ ] **Step 1: 创建 hooks 目录和 useGraph.ts**

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
  forceStrength: number
  setForceStrength: (value: number) => void
  
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
  setSelectedConcept: (concept: Concept | null) => void
  setSelectedPaper: (paper: Paper | null) => void
  setResearchPoints: (points: ResearchPointsResponse | null) => void
  setLoadingResearchPoints: (loading: boolean) => void
}

export function useGraph(): UseGraphReturn {
  // Agent store for context
  const { updateContext } = useAgentStore()

  // Data state
  const [loading, setLoading] = useState(true)
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [edges, setEdges] = useState<GraphEdge[]>([])
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([])
  const [graphLinks, setGraphLinks] = useState<{ source: string; target: string }[]>([])
  const [folders, setFolders] = useState<{ id: string; name: string }[]>([])

  // View state
  const [viewMode, setViewMode] = useState<'all' | 'concept'>('all')
  const [selectedConcept, setSelectedConcept] = useState<Concept | null>(null)
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)
  const [activeFolder, setActiveFolder] = useState<string>('')
  const [forceStrength, setForceStrength] = useState(150)

  // Research points state
  const [researchPoints, setResearchPoints] = useState<ResearchPointsResponse | null>(null)
  const [loadingResearchPoints, setLoadingResearchPoints] = useState(false)

  // Compute depth for each node
  const getNodeDepth = useCallback((nodeId: string, parentMap: Map<string, string>): number => {
    const visited = new Set<string>()
    let depth = 0
    let current = nodeId
    while (parentMap.has(current) && !visited.has(current)) {
      visited.add(current)
      depth++
      current = parentMap.get(current)!
    }
    return depth
  }, [])

  // Load folders
  const loadFolders = useCallback(() => {
    foldersApi.list().then(res => {
      setFolders(res.data)
    })
  }, [])

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      try {
        const graphRes = await graphApi.data(activeFolder)
        const nodesFromGraph = graphRes.data.nodes.map((n: { id: string; label: string; label_en?: string; category?: string; paper_count?: number }) => ({
          id: n.id,
          text: n.label,
          text_en: n.label_en,
          category: n.category,
          paper_count: n.paper_count || 0,
        }))
        setConcepts(nodesFromGraph)
        setEdges(graphRes.data.edges)
        setLoading(false)
      } catch (err) {
        console.error('Failed to load:', err)
        setLoading(false)
      }
    }
    loadData()
    loadFolders()
  }, [activeFolder, loadFolders])

  // Build initial graph data
  useEffect(() => {
    if (loading || concepts.length === 0) return

    const parentMap = new Map<string, string>()
    edges.forEach(e => parentMap.set(e.target, e.source))

    const nodes: GraphNode[] = concepts.map(c => ({
      id: c.id,
      name: c.text,
      name_en: c.text_en,
      type: 'concept' as const,
      category: c.category || 'method',
      paperCount: c.paper_count,
      depth: getNodeDepth(c.id, parentMap),
    }))

    const links = edges.map(e => ({
      source: e.source,
      target: e.target,
    }))

    setGraphNodes(nodes)
    setGraphLinks(links)
    setViewMode('all')
  }, [loading, concepts, edges, getNodeDepth])

  // Handle concept click
  const handleConceptClick = useCallback(async (node: GraphNode) => {
    if (node.type !== 'concept') return

    try {
      const res = await conceptsApi.get(node.id)
      setSelectedConcept(res.data)
      setSelectedPaper(null)

      // Update AI Agent context
      updateContext({
        currentTarget: {
          type: 'concept',
          id: res.data.id,
          name: res.data.text,
        }
      })
    } catch (err) {
      console.error('Failed to get concept:', err)
    }
  }, [updateContext])

  // Enter paper view
  const handleViewPapers = useCallback(() => {
    if (!selectedConcept) return

    const papers = selectedConcept.papers || []
    if (papers.length === 0) return

    const centerNode: GraphNode = {
      id: `center-${selectedConcept.id}`,
      name: selectedConcept.text,
      type: 'center',
      category: selectedConcept.category ?? undefined,
      paperCount: selectedConcept.paper_count,
    }

    const paperNodes: GraphNode[] = papers.map((p: { doi: string; title: string }) => ({
      id: `paper-${p.doi}`,
      name: p.title,
      type: 'paper' as const,
      doi: p.doi,
    }))

    const paperLinks = papers.map((p: { doi: string }) => ({
      source: centerNode.id,
      target: `paper-${p.doi}`,
    }))

    setGraphNodes([centerNode, ...paperNodes])
    setGraphLinks(paperLinks)
    setViewMode('concept')
    setSelectedPaper(null)
  }, [selectedConcept])

  // Handle paper click
  const handlePaperClick = useCallback(async (node: GraphNode) => {
    if (node.type !== 'paper' || !node.doi) return

    try {
      const res = await papersApi.get(node.doi)
      setSelectedPaper(res.data)

      // Update AI Agent context
      updateContext({
        currentTarget: {
          type: 'paper',
          id: node.doi,
          name: res.data.title,
        }
      })
    } catch (err) {
      console.error('Failed to get paper:', err)
    }
  }, [updateContext])

  // Discover research points
  const handleDiscoverResearchPoints = useCallback(async () => {
    if (!selectedConcept) return

    setLoadingResearchPoints(true)
    setResearchPoints(null)

    try {
      const res = await conceptsApi.researchPoints(selectedConcept.id)
      setResearchPoints(res.data)
    } catch (err) {
      console.error('Failed to get research points:', err)
      setResearchPoints({
        concept_id: selectedConcept.id,
        concept_name: selectedConcept.text,
        research_points: [{
          title: 'Analysis Failed',
          hypothesis: '',
          description: 'Could not retrieve research points. Check LLM configuration.',
          discovery_method: 'gap_filling',
          rationale: String(err),
          related_concepts: [],
          difficulty: 'medium',
          difficulty_reason: 'Analysis failed',
          novelty: 'moderate',
          potential_impact: 'niche',
        }],
        analysis_context: {
          concept: { id: selectedConcept.id, name: selectedConcept.text },
          ancestors: [],
          descendants: [],
          edge_nodes: [],
          related_papers: [],
        },
      })
    } finally {
      setLoadingResearchPoints(false)
    }
  }, [selectedConcept])

  // Back to all concepts
  const handleBack = useCallback(() => {
    const parentMap = new Map<string, string>()
    edges.forEach(e => parentMap.set(e.target, e.source))

    const nodes: GraphNode[] = concepts.map(c => ({
      id: c.id,
      name: c.text,
      name_en: c.text_en,
      type: 'concept' as const,
      category: c.category || 'method',
      paperCount: c.paper_count,
      depth: getNodeDepth(c.id, parentMap),
    }))

    const links = edges.map(e => ({
      source: e.source,
      target: e.target,
    }))

    setGraphNodes(nodes)
    setGraphLinks(links)
    setViewMode('all')
    setSelectedConcept(null)
    setSelectedPaper(null)
    setResearchPoints(null)
  }, [concepts, edges, getNodeDepth])

  return {
    // Data
    loading,
    concepts,
    edges,
    graphNodes,
    graphLinks,
    folders,
    
    // View state
    viewMode,
    selectedConcept,
    selectedPaper,
    activeFolder,
    forceStrength,
    setForceStrength,
    
    // Research points
    researchPoints,
    loadingResearchPoints,
    
    // Actions
    handleConceptClick,
    handlePaperClick,
    handleViewPapers,
    handleBack,
    handleDiscoverResearchPoints,
    setActiveFolder,
    loadFolders,
    
    // Graph methods
    getNodeDepth,
    setSelectedConcept,
    setSelectedPaper,
    setResearchPoints,
    setLoadingResearchPoints,
  }
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/pages/ConceptsGraph/hooks/useGraph.ts
git commit -m "feat(frontend): add useGraph hook for ConceptsGraph page"
```

---

## Task 4: 创建 index.tsx

**Files:**
- Create: `frontend/src/pages/ConceptsGraph/index.tsx`

这是最复杂的任务，需要将原文件的 UI 部分移过来并使用 useGraph hook。由于文件较大，分步执行。

- [ ] **Step 1: 创建 index.tsx（主组件框架）**

创建文件，包含导入、状态和基本结构。复制原 ConceptsGraph.tsx 的 JSX 部分，但将状态和回调替换为 useGraph hook。

主要修改：
1. 导入 types 和 constants
2. 使用 useGraph hook 获取状态和方法
3. 保留 UI 相关的本地状态（dedupOpen, filterPanelOpen 等）
4. 保留 ForceGraph 配置和渲染逻辑

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd D:/meta-knowledge-graph-main/frontend
npx tsc --noEmit
```

Expected: No errors

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/ConceptsGraph/index.tsx
git commit -m "feat(frontend): create ConceptsGraph index component with useGraph hook"
```

---

## Task 5: 删除旧文件并验证

**Files:**
- Delete: `frontend/src/pages/ConceptsGraph.tsx`

- [ ] **Step 1: 删除旧文件**

```bash
rm frontend/src/pages/ConceptsGraph.tsx
```

- [ ] **Step 2: 验证导入路径**

确保路由和其他引用仍然有效：
```bash
cd D:/meta-knowledge-graph-main/frontend
npx tsc --noEmit
```

Expected: No errors

- [ ] **Step 3: 最终提交**

```bash
git add -A
git commit -m "refactor(frontend): split ConceptsGraph page into modular structure

- Extract types to types.ts (~50 lines)
- Extract constants to constants.ts (~20 lines)
- Create useGraph hook with state and logic (~300 lines)
- Simplify index.tsx to UI rendering (~400 lines)
- Max file size reduced from 1612 to ~400 lines
- Backward compatible: import path unchanged"
```

---

## 预期结果

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| 最大文件行数 | 1612 | ~400 |
| 文件数 | 1 | 4 |
| 类型可复用 | ❌ | ✅ |
| Hook 可测试 | ❌ | ✅ |
| 向后兼容 | N/A | ✅ |