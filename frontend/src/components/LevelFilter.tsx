// frontend/src/components/LevelFilter.tsx
import React from 'react'
import { Layers } from 'lucide-react'

export interface LevelRange {
  min: number
  max: number
}

interface LevelFilterProps {
  value: LevelRange
  onChange: (range: LevelRange) => void
  maxLevel?: number
}

const LEVEL_LABELS = [
  { level: 0, label: 'L0 领域', short: '领域' },
  { level: 1, label: 'L1 方向', short: '方向' },
  { level: 2, label: 'L2 子方向', short: '子方向' },
  { level: 3, label: 'L3 任务', short: '任务' },
  { level: 4, label: 'L4 方法', short: '方法' },
  { level: 5, label: 'L5 技术', short: '技术' },
]

const PRESETS = [
  { label: '概览', min: 0, max: 2 },
  { label: '标准', min: 0, max: 4 },
  { label: '全部', min: 0, max: 5 },
]

export function LevelFilter({ value, onChange, maxLevel = 5 }: LevelFilterProps) {
  const handlePresetClick = (preset: typeof PRESETS[0]) => {
    onChange({ min: preset.min, max: Math.min(preset.max, maxLevel) })
  }

  const handleMinChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newMin = parseInt(e.target.value, 10)
    const newMax = Math.max(value.max, newMin)
    onChange({ min: newMin, max: newMax })
  }

  const handleMaxChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newMax = parseInt(e.target.value, 10)
    const newMin = Math.min(value.min, newMax)
    onChange({ min: newMin, max: newMax })
  }

  return (
    <div className="bg-white/90 backdrop-blur rounded-xl shadow-lg p-3 z-10">
      <div className="flex items-center gap-2 mb-3">
        <Layers className="w-4 h-4 text-gray-500" />
        <span className="text-xs font-semibold text-gray-600">层级筛选</span>
      </div>

      {/* 快捷按钮 */}
      <div className="flex gap-1 mb-3">
        {PRESETS.map((preset) => (
          <button
            key={preset.label}
            onClick={() => handlePresetClick(preset)}
            className={`px-2 py-1 text-xs rounded-lg transition-colors ${
              value.min === preset.min && value.max === Math.min(preset.max, maxLevel)
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* 范围选择 */}
      <div className="flex items-center gap-2">
        <select
          value={value.min}
          onChange={handleMinChange}
          className="text-xs px-2 py-1 rounded-lg border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {LEVEL_LABELS.slice(0, maxLevel + 1).map((item) => (
            <option key={item.level} value={item.level}>
              {item.short}
            </option>
          ))}
        </select>
        <span className="text-xs text-gray-400">至</span>
        <select
          value={value.max}
          onChange={handleMaxChange}
          className="text-xs px-2 py-1 rounded-lg border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {LEVEL_LABELS.slice(0, maxLevel + 1).map((item) => (
            <option key={item.level} value={item.level}>
              {item.short}
            </option>
          ))}
        </select>
      </div>

      {/* 当前范围显示 */}
      <div className="mt-2 text-xs text-gray-500 text-center">
        显示 {LEVEL_LABELS[value.min].short} ~ {LEVEL_LABELS[value.max].short}
      </div>
    </div>
  )
}