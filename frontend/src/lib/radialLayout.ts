// 层级配置
export const LEVEL_CONFIG = {
  field: { level: 0, radius: 80, nodeSize: 18, opacity: 1.0 },
  direction: { level: 1, radius: 140, nodeSize: 14, opacity: 0.95 },
  subdirection: { level: 2, radius: 200, nodeSize: 11, opacity: 0.85 },
  task: { level: 3, radius: 260, nodeSize: 9, opacity: 0.75 },
  method: { level: 4, radius: 320, nodeSize: 7, opacity: 0.65 },
  technique: { level: 5, radius: 380, nodeSize: 5, opacity: 0.55 },
} as const

export type Category = keyof typeof LEVEL_CONFIG

export interface RadialLayoutConfig {
  centerX: number
  centerY: number
  ringSpacing: number // 环之间的间距
  minSectorAngle: number // 最小扇区角度（弧度）
}

export interface ConceptNode {
  id: string
  text: string
  category: Category
  paper_count: number
  parentId?: string | null
  children?: ConceptNode[]
}

const DEFAULT_CONFIG: RadialLayoutConfig = {
  centerX: 600,
  centerY: 400,
  ringSpacing: 60,
  minSectorAngle: Math.PI / 36, // 5度
}

/**
 * 查找根概念（没有父节点的概念）
 */
export function findRoots(
  concepts: ConceptNode[],
  edges: { source: string; target: string }[]
): ConceptNode[] {
  const childIds = new Set(edges.map(e => e.target))
  return concepts.filter(c => !childIds.has(c.id))
}

/**
 * 构建父子关系映射
 */
export function buildParentMap(
  edges: { source: string; target: string }[]
): Map<string, string> {
  const map = new Map<string, string>()
  edges.forEach(e => map.set(e.target, e.source))
  return map
}

/**
 * 构建子节点映射
 */
export function buildChildrenMap(
  edges: { source: string; target: string }[]
): Map<string, string[]> {
  const map = new Map<string, string[]>()
  edges.forEach(e => {
    const children = map.get(e.source) || []
    children.push(e.target)
    map.set(e.source, children)
  })
  return map
}

/**
 * 计算概念深度
 */
export function computeDepth(
  conceptId: string,
  parentMap: Map<string, string>,
  cache: Map<string, number> = new Map()
): number {
  if (cache.has(conceptId)) return cache.get(conceptId)!

  const parentId = parentMap.get(conceptId)
  if (!parentId) {
    cache.set(conceptId, 0)
    return 0
  }

  const depth = 1 + computeDepth(parentId, parentMap, cache)
  cache.set(conceptId, depth)
  return depth
}

/**
 * 放射状布局主函数
 */
export function computeRadialLayout(
  concepts: ConceptNode[],
  edges: { source: string; target: string }[],
  config: Partial<RadialLayoutConfig> = {}
): Map<string, { x: number; y: number; angle: number; level: number }> {
  const cfg = { ...DEFAULT_CONFIG, ...config }
  const positions = new Map<string, { x: number; y: number; angle: number; level: number }>()

  const parentMap = buildParentMap(edges)
  const childrenMap = buildChildrenMap(edges)
  const depthCache = new Map<string, number>()

  // 计算每个概念的深度
  concepts.forEach(c => {
    computeDepth(c.id, parentMap, depthCache)
  })

  // 找到根概念
  const roots = findRoots(concepts, edges)

  if (roots.length === 0) {
    // 没有根概念，使用力导向布局的回退
    concepts.forEach((c, i) => {
      const angle = (2 * Math.PI * i) / concepts.length
      const level = depthCache.get(c.id) || 0
      const radius = cfg.ringSpacing * (level + 1)
      positions.set(c.id, {
        x: cfg.centerX + radius * Math.cos(angle),
        y: cfg.centerY + radius * Math.sin(angle),
        angle,
        level,
      })
    })
    return positions
  }

  // 计算每个根的扇区角度范围
  const sectorAngle = (2 * Math.PI) / roots.length

  // 递归布局每个根的子树
  roots.forEach((root, rootIndex) => {
    const sectorStart = rootIndex * sectorAngle
    const sectorEnd = (rootIndex + 1) * sectorAngle

    layoutSubtree(
      root.id,
      cfg.centerX,
      cfg.centerY,
      sectorStart,
      sectorEnd,
      0,
      positions,
      childrenMap,
      depthCache,
      cfg
    )
  })

  return positions
}

/**
 * 递归布局子树
 */
function layoutSubtree(
  nodeId: string,
  centerX: number,
  centerY: number,
  sectorStart: number,
  sectorEnd: number,
  depth: number,
  positions: Map<string, { x: number; y: number; angle: number; level: number }>,
  childrenMap: Map<string, string[]>,
  depthCache: Map<string, number>,
  config: RadialLayoutConfig
): void {
  const radius = config.ringSpacing * (depth + 1)
  const midAngle = (sectorStart + sectorEnd) / 2

  // 计算位置
  positions.set(nodeId, {
    x: centerX + radius * Math.cos(midAngle),
    y: centerY + radius * Math.sin(midAngle),
    angle: midAngle,
    level: depth,
  })

  // 布局子节点
  const children = childrenMap.get(nodeId) || []
  if (children.length === 0) return

  // 计算子节点扇区
  const childSectorAngle = (sectorEnd - sectorStart) / children.length

  children.forEach((childId, index) => {
    const childSectorStart = sectorStart + index * childSectorAngle
    const childSectorEnd = childSectorStart + childSectorAngle

    layoutSubtree(
      childId,
      centerX,
      centerY,
      childSectorStart,
      childSectorEnd,
      depth + 1,
      positions,
      childrenMap,
      depthCache,
      config
    )
  })
}

/**
 * 根据层级过滤节点
 */
export function filterByLevel(
  positions: Map<string, { x: number; y: number; angle: number; level: number }>,
  minLevel: number,
  maxLevel: number
): Set<string> {
  const visible = new Set<string>()
  positions.forEach((pos, id) => {
    if (pos.level >= minLevel && pos.level <= maxLevel) {
      visible.add(id)
    }
  })
  return visible
}

/**
 * 获取节点的完整路径（从根到该节点）
 */
export function getNodePath(
  nodeId: string,
  parentMap: Map<string, string>
): string[] {
  const path: string[] = [nodeId]
  let current = nodeId

  while (parentMap.has(current)) {
    const parentId = parentMap.get(current)!
    path.unshift(parentId)
    current = parentId
  }

  return path
}

/**
 * 获取节点的所有后代
 */
export function getDescendants(
  nodeId: string,
  childrenMap: Map<string, string[]>
): string[] {
  const descendants: string[] = []
  const stack = [nodeId]

  while (stack.length > 0) {
    const current = stack.pop()!
    const children = childrenMap.get(current) || []
    children.forEach(child => {
      descendants.push(child)
      stack.push(child)
    })
  }

  return descendants
}

/**
 * 计算扇区背景路径
 */
export function computeSectorPath(
  centerX: number,
  centerY: number,
  startAngle: number,
  endAngle: number,
  innerRadius: number,
  outerRadius: number
): string {
  const startOuter = {
    x: centerX + outerRadius * Math.cos(startAngle),
    y: centerY + outerRadius * Math.sin(startAngle),
  }
  const endOuter = {
    x: centerX + outerRadius * Math.cos(endAngle),
    y: centerY + outerRadius * Math.sin(endAngle),
  }
  const startInner = {
    x: centerX + innerRadius * Math.cos(startAngle),
    y: centerY + innerRadius * Math.sin(startAngle),
  }
  const endInner = {
    x: centerX + innerRadius * Math.cos(endAngle),
    y: centerY + innerRadius * Math.sin(endAngle),
  }

  const largeArc = endAngle - startAngle > Math.PI ? 1 : 0

  return [
    `M ${startInner.x} ${startInner.y}`,
    `L ${startOuter.x} ${startOuter.y}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArc} 1 ${endOuter.x} ${endOuter.y}`,
    `L ${endInner.x} ${endInner.y}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${startInner.x} ${startInner.y}`,
    'Z',
  ].join(' ')
}