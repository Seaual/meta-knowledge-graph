// frontend/src/components/Breadcrumb.tsx
import React from 'react'
import { ChevronRight, Home } from 'lucide-react'

export interface BreadcrumbItem {
  id: string
  text: string
  category: string
}

interface BreadcrumbProps {
  items: BreadcrumbItem[]
  onItemClick: (id: string, index: number) => void
  onHomeClick: () => void
}

const CATEGORY_COLORS: Record<string, string> = {
  field: '#FF6B6B',
  direction: '#4ECDC4',
  subdirection: '#45B7D1',
  task: '#96CEB4',
  method: '#FFA726',
  technique: '#FFD93D',
}

export function Breadcrumb({ items, onItemClick, onHomeClick }: BreadcrumbProps) {
  return (
    <div className="flex items-center gap-1 bg-white/90 backdrop-blur rounded-xl shadow-lg px-3 py-2 z-10">
      {/* 首页按钮 */}
      <button
        onClick={onHomeClick}
        className="flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-gray-100 transition-colors text-gray-600 hover:text-gray-900"
        title="返回总览"
      >
        <Home className="w-4 h-4" />
        <span className="text-xs font-medium">总览</span>
      </button>

      {/* 面包屑项 */}
      {items.map((item, index) => (
        <React.Fragment key={item.id}>
          <ChevronRight className="w-4 h-4 text-gray-400" />
          <button
            onClick={() => onItemClick(item.id, index)}
            className={`px-2 py-1 rounded-lg text-xs font-medium transition-colors ${
              index === items.length - 1
                ? 'bg-gray-100 text-gray-900'
                : 'hover:bg-gray-100 text-gray-600 hover:text-gray-900'
            }`}
            style={{
              borderLeft: index === items.length - 1 ? `3px solid ${CATEGORY_COLORS[item.category] || '#94A3B8'}` : 'none',
            }}
          >
            {item.text}
          </button>
        </React.Fragment>
      ))}
    </div>
  )
}