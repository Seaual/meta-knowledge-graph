import { useEffect, useState } from 'react'
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { graphApi } from '../lib/api'

interface GraphNode {
  id: string
  label: string
  category: string
  paper_count: number
}

interface GraphEdge {
  source: string
  target: string
  type: string
}

interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

const categoryColors: Record<string, string> = {
  field: '#3b82f6',
  direction: '#10b981',
  method: '#f59e0b',
  technique: '#ef4444',
  detail: '#8b5cf6',
}

export default function Graph() {
  const [loading, setLoading] = useState(true)
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  useEffect(() => {
    graphApi.data().then(res => {
      const data: GraphData = res.data
      convertToReactFlow(data)
      setLoading(false)
    })
  }, [])

  const convertToReactFlow = (data: GraphData) => {
    // Create nodes with simple layout
    const rfNodes: Node[] = data.nodes.map((node, index) => ({
      id: node.id,
      type: 'default',
      data: {
        label: (
          <div className="text-center">
            <div className="font-medium text-sm">{node.label}</div>
            <div className="text-xs text-gray-500">({node.paper_count})</div>
          </div>
        ),
      },
      position: {
        x: (index % 10) * 200,
        y: Math.floor(index / 10) * 150,
      },
      style: {
        backgroundColor: categoryColors[node.category] || '#6b7280',
        color: 'white',
        borderRadius: '8px',
        padding: '8px 12px',
        fontSize: '12px',
      },
    }))

    // Create edges
    const rfEdges: Edge[] = data.edges.map((edge, index) => ({
      id: `e${index}`,
      source: edge.source,
      target: edge.target,
      animated: true,
      style: { stroke: '#94a3b8' },
    }))

    setNodes(rfNodes as Node[])
    setEdges(rfEdges as Edge[])
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        加载图谱中...
      </div>
    )
  }

  if (nodes.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">知识图谱</h1>
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-500">暂无图谱数据</p>
          <p className="text-sm text-gray-400 mt-2">请先上传并处理论文</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">知识图谱</h1>
        <div className="flex gap-4 text-sm">
          {Object.entries(categoryColors).map(([cat, color]) => (
            <div key={cat} className="flex items-center gap-1">
              <div
                className="w-3 h-3 rounded"
                style={{ backgroundColor: color }}
              />
              <span className="text-gray-600 capitalize">{cat}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow" style={{ height: '70vh' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          attributionPosition="bottom-left"
        >
          <Background />
          <Controls />
          <MiniMap
            nodeColor={(node) => categoryColors[node.data?.category as string] || '#6b7280'}
            maskColor="rgba(0,0,0,0.1)"
          />
        </ReactFlow>
      </div>
    </div>
  )
}