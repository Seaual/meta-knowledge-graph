// frontend/src/components/ConceptGraphInChat.tsx
// 聊天中嵌入的完整概念图谱组件

import { useEffect, useRef, useState, useCallback } from 'react'
import ForceGraph from 'force-graph'
import { forceManyBody, forceLink, forceCollide } from 'd3-force'
import { ConceptNode } from '../stores/agentStore'

interface Props {
  data: ConceptNode
  onNodeClick?: (node: ConceptNode) => void
}

// 配色方案 - 学术风格
const CENTER_COLOR = '#d4a012'    // 金色 - 中心概念
const PARENT_COLOR = '#8b4513'    // 深棕色 - 父概念
const CHILD_COLOR = '#4a6fa5'     // 钢蓝色 - 子概念
const BG_COLOR = '#faf8f5'        // 米白背景

export default function ConceptGraphInChat({ data, onNodeClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<any>(null)

  // 初始化图谱
  const initGraph = useCallback(() => {
    if (!containerRef.current || !data) return

    const width = containerRef.current.clientWidth || 600
    const height = 380

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
    data.children?.forEach((child) => {
      nodes.push({
        id: child.id,
        name: child.name,
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
    })

    // 添加父概念
    data.parents?.forEach((parent) => {
      nodes.push({
        id: parent.id,
        name: parent.name,
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
    })

    // 销毁旧图谱
    if (graphRef.current) {
      graphRef.current._destructor()
    }

    // 创建完整概念图谱
    const graph = new ForceGraph(containerRef.current)
      .graphData({ nodes, links })
      .width(width)
      .height(height)
      .backgroundColor(BG_COLOR)
      .nodeId('id')
      .nodeVal('val')
      .nodeLabel((node: any) => `${node.name}\n📚 ${node.paperCount || 0} 篇论文`)
      .nodeColor((node: any) => {
        if (node.type === 'center') return CENTER_COLOR
        if (node.type === 'parent') return PARENT_COLOR
        return CHILD_COLOR
      })
      .nodeCanvasObject((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const isCenter = node.type === 'center'
        const isParent = node.type === 'parent'

        // 节点大小根据论文数缩放
        const baseSize = isCenter ? 18 : isParent ? 14 : 10
        const size = baseSize + Math.sqrt(node.paperCount || 0) * 0.8

        const x = node.x
        const y = node.y

        // 绘制光晕效果
        if (isCenter) {
          const gradient = ctx.createRadialGradient(x, y, 0, x, y, size * 2)
          gradient.addColorStop(0, 'rgba(212, 160, 18, 0.3)')
          gradient.addColorStop(1, 'rgba(212, 160, 18, 0)')
          ctx.beginPath()
          ctx.arc(x, y, size * 2, 0, 2 * Math.PI)
          ctx.fillStyle = gradient
          ctx.fill()
        }

        // 绘制节点阴影
        ctx.beginPath()
        ctx.arc(x + 2, y + 2, size, 0, 2 * Math.PI)
        ctx.fillStyle = 'rgba(0, 0, 0, 0.1)'
        ctx.fill()

        // 绘制节点
        ctx.beginPath()
        ctx.arc(x, y, size, 0, 2 * Math.PI)
        const nodeGradient = ctx.createRadialGradient(x - size/3, y - size/3, 0, x, y, size)
        if (isCenter) {
          nodeGradient.addColorStop(0, '#f0c040')
          nodeGradient.addColorStop(1, CENTER_COLOR)
        } else if (isParent) {
          nodeGradient.addColorStop(0, '#a0522d')
          nodeGradient.addColorStop(1, PARENT_COLOR)
        } else {
          nodeGradient.addColorStop(0, '#6b8fc7')
          nodeGradient.addColorStop(1, CHILD_COLOR)
        }
        ctx.fillStyle = nodeGradient
        ctx.fill()

        // 绘制边框
        ctx.strokeStyle = isCenter ? '#b8860b' : 'rgba(0, 0, 0, 0.2)'
        ctx.lineWidth = isCenter ? 2 : 1
        ctx.stroke()

        // 显示名称
        if (globalScale > 0.6) {
          const fontSize = isCenter ? 12 : isParent ? 11 : 10
          ctx.font = `500 ${fontSize}px "DM Sans", sans-serif`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'top'

          const displayName = node.name.length > 12 ? node.name.slice(0, 12) + '...' : node.name

          // 文字背景
          const textWidth = ctx.measureText(displayName).width
          ctx.fillStyle = 'rgba(250, 248, 245, 0.9)'
          ctx.fillRect(x - textWidth/2 - 4, y + size + 4, textWidth + 8, fontSize + 4)

          // 文字
          ctx.fillStyle = '#2c1810'
          ctx.fillText(displayName, x, y + size + 6)

          // 论文数量
          if (node.paperCount > 0 && globalScale > 0.8) {
            ctx.font = `400 9px "DM Sans", sans-serif`
            ctx.fillStyle = '#666'
            ctx.fillText(`${node.paperCount}篇`, x, y + size + fontSize + 10)
          }
        }
      })
      .linkColor((link: any) => {
        if (link.type === 'parent') return 'rgba(139, 69, 19, 0.4)'
        return 'rgba(74, 111, 165, 0.4)'
      })
      .linkWidth(2)
      .linkDirectionalParticles(2)
      .linkDirectionalParticleWidth(3)
      .linkDirectionalParticleColor((link: any) => {
        if (link.type === 'parent') return PARENT_COLOR
        return CHILD_COLOR
      })
      .d3AlphaDecay(0.02)
      .d3VelocityDecay(0.3)
      .d3Force('charge', forceManyBody().strength(-200))
      .d3Force('collide', forceCollide().radius((node: any) => (node.val || 1) * 15))
      // 交互设置
      .enableZoomInteraction(true)      // 启用缩放
      .enableNodeDrag(true)             // 启用节点拖拽
      .enablePanInteraction(true)       // 启用画布拖动
      .minZoom(0.3)
      .maxZoom(4)
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

    // 启动动画
    graphRef.current = graph

    // 延迟调整视图
    setTimeout(() => {
      if (graphRef.current) {
        graphRef.current.zoomToFit(400, 50)
      }
    }, 100)

    return () => {
      if (graphRef.current) {
        graphRef.current._destructor()
        graphRef.current = null
      }
    }
  }, [data, onNodeClick])

  useEffect(() => {
    initGraph()
  }, [initGraph])

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
            {data.name}
          </span>
        </div>

        {/* 图谱容器 - 确保 pointer-events 正常 */}
        <div
          ref={containerRef}
          style={{
            width: dimensions.width,
            height: dimensions.height,
            cursor: 'grab',
            pointerEvents: 'auto'
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