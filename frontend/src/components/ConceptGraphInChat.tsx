// frontend/src/components/ConceptGraphInChat.tsx
// 聊天中嵌入的概念图谱组件 - 与概念页面风格一致

import { useEffect, useRef, useState } from 'react'
import ForceGraph from 'force-graph'
import { forceManyBody, forceCollide, forceLink } from 'd3-force'
import { ConceptNode } from '../stores/agentStore'

interface Props {
  data: ConceptNode
  onNodeClick?: (node: ConceptNode) => void
}

// Category colors - 与概念页面一致
const CATEGORY_COLORS: Record<string, string> = {
  field: '#6b4423',        // sepia
  direction: '#b8860b',    // amber
  subdirection: '#9a6b3c', // copper
  task: '#4a6b8a',         // slate blue
  method: '#c2410c',       // terracotta
  technique: '#2d5a27',    // forest green
  dataset: '#5c4d7d',      // purple
  finding: '#d4a012',      // gold
}

const PARENT_COLOR = '#8b4513'   // 深棕色 - 父概念
const CHILD_COLOR = '#4a6fa5'    // 钢蓝色 - 子概念
const CENTER_COLOR = '#d4a012'   // 金色 - 中心概念

export default function ConceptGraphInChat({ data, onNodeClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setError(null)

    if (!containerRef.current) {
      console.log('ConceptGraph: container ref is null')
      return
    }

    if (!data || !data.id || !data.name) {
      console.log('ConceptGraph: invalid data', data)
      setError('图谱数据无效')
      return
    }

    console.log('ConceptGraph: rendering with data', data)

    try {
      // 构建节点和边
      const nodes: any[] = [
        {
          id: data.id,
          name: data.name,
          type: 'center',
          paperCount: data.paper_count || 0,
          category: data.category,
          val: 3
        },
      ]

      const links: any[] = []

      // 添加子概念
      if (Array.isArray(data.children)) {
        data.children.forEach((child) => {
          if (child && child.id) {
            nodes.push({
              id: child.id,
              name: child.name || 'Unknown',
              type: 'child',
              paperCount: child.paper_count || 0,
              category: child.category,
              val: 1.5
            })
            links.push({
              source: data.id,
              target: child.id,
              type: 'child'
            })
          }
        })
      }

      // 添加父概念
      if (Array.isArray(data.parents)) {
        data.parents.forEach((parent) => {
          if (parent && parent.id) {
            nodes.push({
              id: parent.id,
              name: parent.name || 'Unknown',
              type: 'parent',
              paperCount: parent.paper_count || 0,
              category: parent.category,
              val: 2
            })
            links.push({
              source: parent.id,
              target: data.id,
              type: 'parent'
            })
          }
        })
      }

      console.log('ConceptGraph: nodes', nodes.length, 'links', links.length)

      // 销毁旧图谱
      if (graphRef.current) {
        try {
          graphRef.current._destructor()
        } catch (e) {
          console.warn('ConceptGraph: error destroying old graph', e)
        }
        graphRef.current = null
      }

      // 创建概念图谱 - 与概念页面风格一致
      const graph = new ForceGraph(containerRef.current)
        .graphData({ nodes, links })
        .nodeId('id')
        .nodeLabel((node: any) => `${node.name}\n📚 ${node.paperCount || 0} 篇论文`)
        .nodeVal((node: any) => {
          if (node.type === 'center') return 3
          if (node.type === 'parent') return 2
          return 1.5
        })
        .nodeCanvasObject((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const isCenter = node.type === 'center'
          const isParent = node.type === 'parent'
          const isChild = node.type === 'child'

          // 节点大小
          let size: number
          let color: string

          if (isCenter) {
            size = 18
            color = CENTER_COLOR
          } else if (isParent) {
            size = 14 + Math.sqrt(node.paperCount || 0) * 0.3
            color = PARENT_COLOR
          } else {
            // 子概念根据类别着色
            const baseSize = node.category ? (CATEGORY_COLORS[node.category] ? 12 : 10) : 10
            size = baseSize + Math.sqrt(node.paperCount || 0) * 0.3
            color = node.category && CATEGORY_COLORS[node.category]
              ? CATEGORY_COLORS[node.category]
              : CHILD_COLOR
          }

          const x = node.x || 0
          const y = node.y || 0

          // 中心节点光晕效果
          if (isCenter) {
            const gradient = ctx.createRadialGradient(x, y, 0, x, y, size * 1.5)
            gradient.addColorStop(0, color + '40')
            gradient.addColorStop(1, color + '10')
            ctx.beginPath()
            ctx.arc(x, y, size * 1.5, 0, 2 * Math.PI)
            ctx.fillStyle = gradient
            ctx.fill()
          }

          // 绘制节点 - 与概念页面一致的空心圆形风格
          ctx.beginPath()
          ctx.arc(x, y, size, 0, 2 * Math.PI)

          if (isCenter) {
            // 中心节点：渐变填充 + 粗边框 + 中心实心圆
            const gradient = ctx.createRadialGradient(x, y, 0, x, y, size)
            gradient.addColorStop(0, color + '60')
            gradient.addColorStop(1, color + '20')
            ctx.fillStyle = gradient
            ctx.fill()
            ctx.strokeStyle = color
            ctx.lineWidth = 3 / globalScale
            ctx.stroke()
            // 中心实心圆
            ctx.beginPath()
            ctx.arc(x, y, size * 0.5, 0, 2 * Math.PI)
            ctx.fillStyle = color
            ctx.fill()
          } else {
            // 其他节点：半透明填充 + 边框 + 小实心圆（与概念页面一致）
            ctx.fillStyle = color + '30'
            ctx.fill()
            ctx.strokeStyle = color
            ctx.lineWidth = 2 / globalScale
            ctx.stroke()
            // 中心小圆点
            ctx.beginPath()
            ctx.arc(x, y, size * 0.3, 0, 2 * Math.PI)
            ctx.fillStyle = color
            ctx.fill()
          }

          // 绘制标签
          if (globalScale > 0.5) {
            const fontSize = isCenter ? 14 : 11
            ctx.font = `500 ${fontSize}px "Source Sans 3", sans-serif`
            ctx.textAlign = 'center'
            ctx.textBaseline = 'top'
            ctx.fillStyle = '#2c1810'

            const displayName = node.name && node.name.length > 20
              ? node.name.substring(0, 20) + '...'
              : (node.name || '')

            ctx.fillText(displayName, x, y + size + 4)
          }
        })
        .linkColor((link: any) => {
          if (link.type === 'parent') return PARENT_COLOR + '60'
          return CHILD_COLOR + '60'
        })
        .linkWidth(2)
        .linkDirectionalParticles(2)
        .linkDirectionalParticleWidth(2)
        .linkDirectionalParticleColor((link: any) => {
          if (link.type === 'parent') return PARENT_COLOR
          return CHILD_COLOR
        })
        .d3AlphaDecay(0.02)
        .d3VelocityDecay(0.3)
        .d3Force('charge', forceManyBody().strength((node: any) => {
          if (node.type === 'center') return -300
          if (node.type === 'parent') return -200
          return -150
        }))
        .d3Force('collision', forceCollide().radius((node: any) => {
          if (node.type === 'center') return 25
          if (node.type === 'parent') return 20
          return 16
        }))
        .onNodeClick((node: any) => {
          if (onNodeClick && node) {
            onNodeClick({
              id: node.id,
              name: node.name,
              category: node.category,
              paper_count: node.paperCount || 0,
            })
          }
        })
        .cooldownTicks(100)
        .onEngineStop(() => {
          if (graphRef.current) {
            graphRef.current.zoomToFit(400, 50)
          }
        })

      graphRef.current = graph

    } catch (e: any) {
      console.error('ConceptGraph: error creating graph', e)
      setError(`图谱渲染错误: ${e.message || '未知错误'}`)
    }

    return () => {
      if (graphRef.current) {
        try {
          graphRef.current._destructor()
        } catch (e) {
          console.warn('ConceptGraph: error in cleanup', e)
        }
        graphRef.current = null
      }
    }
  }, [data, onNodeClick])

  if (error) {
    return (
      <div className="my-3 p-4 rounded-xl bg-red-50 border border-red-200">
        <p className="text-red-600 text-sm">{error}</p>
      </div>
    )
  }

  return (
    <div className="concept-graph-in-chat my-3">
      <div
        className="rounded-xl overflow-hidden shadow-lg"
        style={{
          background: 'linear-gradient(135deg, #faf8f5 0%, #f5f0e8 100%)',
          border: '1px solid rgba(184, 134, 11, 0.15)',
        }}
      >
        {/* 标题栏 */}
        <div
          className="px-4 py-2 flex items-center justify-between"
          style={{
            background: 'rgba(184, 134, 11, 0.08)',
            borderBottom: '1px solid rgba(184, 134, 11, 0.1)'
          }}
        >
          <span className="text-sm font-medium" style={{ color: '#8b4513' }}>
            📊 概念图谱
          </span>
          <span className="text-xs" style={{ color: '#666' }}>
            {data?.name || '未知概念'}
          </span>
        </div>

        {/* 图谱容器 */}
        <div
          ref={containerRef}
          style={{
            width: '100%',
            height: 380,
            minWidth: 400,
            cursor: 'grab'
          }}
        />

        {/* 图例 */}
        <div
          className="px-4 py-2 flex items-center justify-center gap-6 text-xs"
          style={{
            borderTop: '1px solid rgba(184, 134, 11, 0.1)',
            background: 'rgba(255, 255, 255, 0.5)'
          }}
        >
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full shadow-sm" style={{ background: PARENT_COLOR }} />
            <span style={{ color: '#666' }}>父概念</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full shadow-sm" style={{ background: CENTER_COLOR }} />
            <span style={{ color: '#666' }}>当前概念</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full shadow-sm" style={{ background: CHILD_COLOR }} />
            <span style={{ color: '#666' }}>子概念</span>
          </span>
        </div>
      </div>
    </div>
  )
}