import { useState, useEffect, useRef } from 'react'
import { X, RefreshCw, Check, AlertCircle, Merge } from 'lucide-react'
import { dedupApi } from '../lib/api'

// Types
interface MergeSuggestion {
  id: string
  source: { id: string; text: string; paper_count: number }
  target: { id: string; text: string; paper_count: number }
  confidence: number
  rationale: string
}

interface ExecuteDetail {
  source: string
  target: string
  status: 'success' | 'failed'
  message?: string
}

type PanelState = 'idle' | 'scanning' | 'review' | 'executing' | 'result'

interface ScanProgress {
  scanId: string | null
  totalConcepts: number
  conceptsScanned: number
  progress: number
  estimatedTime: number
}

interface DedupPanelProps {
  isOpen: boolean
  onClose: () => void
}

export default function DedupPanel({ isOpen, onClose }: DedupPanelProps) {
  const [panelState, setPanelState] = useState<PanelState>('idle')
  const [scanId, setScanId] = useState<string>('')
  const [suggestions, setSuggestions] = useState<MergeSuggestion[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [executeDetails, setExecuteDetails] = useState<ExecuteDetail[]>([])
  const [error, setError] = useState<string | null>(null)
  const [scanProgress, setScanProgress] = useState<ScanProgress>({
    scanId: null,
    totalConcepts: 0,
    conceptsScanned: 0,
    progress: 0,
    estimatedTime: 0
  })
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const handleScan = async () => {
    setPanelState('scanning')
    setError(null)
    setScanProgress({
      scanId: null,
      totalConcepts: 0,
      conceptsScanned: 0,
      progress: 0,
      estimatedTime: 0
    })

    try {
      // Start scan
      const res = await dedupApi.scan()
      const scanId = res.data.scan_id

      setScanProgress(prev => ({
        ...prev,
        scanId,
        totalConcepts: res.data.total_concepts
      }))

      // Start polling
      startPolling(scanId)
    } catch (err: any) {
      setError(err.response?.data?.detail || '扫描启动失败')
      setPanelState('idle')
    }
  }

  const startPolling = (scanId: string) => {
    // Clear existing polling
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
    }

    pollingRef.current = setInterval(async () => {
      try {
        const res = await dedupApi.scanStatus(scanId)
        const data = res.data

        setScanProgress({
          scanId,
          totalConcepts: data.total_concepts,
          conceptsScanned: data.concepts_scanned,
          progress: data.progress,
          estimatedTime: data.estimated_time
        })

        if (data.status === 'completed') {
          // Stop polling
          if (pollingRef.current) {
            clearInterval(pollingRef.current)
            pollingRef.current = null
          }

          if (data.suggestions) {
            setSuggestions(data.suggestions)
            setSelectedIds(new Set(data.suggestions.map(s => s.id)))
          } else {
            setSuggestions([])
          }
          setPanelState('review')
        } else if (data.status === 'failed') {
          if (pollingRef.current) {
            clearInterval(pollingRef.current)
            pollingRef.current = null
          }
          setError(data.error || '扫描失败')
          setPanelState('idle')
        }
      } catch (err: any) {
        console.error('Poll error:', err)
        // 如果连续失败，设置错误状态
        setError('获取扫描状态失败，请检查网络连接')
      }
    }, 1000) // Poll every second
  }

  const handleExecute = async () => {
    setPanelState('executing')
    setError(null)
    try {
      const res = await dedupApi.execute(scanId, Array.from(selectedIds))
      setExecuteDetails(res.data.details)
      setPanelState('result')
    } catch (err: any) {
      setError(err.response?.data?.detail || '执行失败')
      setPanelState('review')
    }
  }

  const toggleSelection = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleReset = () => {
    setPanelState('idle')
    setScanId('')
    setSuggestions([])
    setSelectedIds(new Set())
    setExecuteDetails([])
    setError(null)
    setScanProgress({
      scanId: null,
      totalConcepts: 0,
      conceptsScanned: 0,
      progress: 0,
      estimatedTime: 0
    })
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'bg-green-100 text-green-700'
    if (confidence >= 0.7) return 'bg-yellow-100 text-yellow-700'
    return 'bg-gray-100 text-gray-600'
  }

  const formatScanTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds}秒`
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    if (minutes < 60) return `${minutes}分${secs > 0 ? secs + '秒' : ''}`
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return `${hours}小时${mins > 0 ? mins + '分' : ''}`
  }

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [])

  if (!isOpen) return null

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-white shadow-2xl z-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <Merge className="w-5 h-5 text-blue-500" />
          <h2 className="font-semibold text-lg">概念去重</h2>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg">
          <X className="w-5 h-5 text-gray-500" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Error */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Idle State */}
        {panelState === 'idle' && (
          <div className="text-center py-12">
            <Merge className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 mb-4">扫描知识图谱中的重复概念</p>
            <button
              onClick={handleScan}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              开始扫描
            </button>
          </div>
        )}

        {/* Scanning State */}
        {panelState === 'scanning' && (
          <div className="text-center py-12">
            <RefreshCw className="w-12 h-12 text-blue-500 mx-auto mb-4 animate-spin" />
            <p className="text-gray-600">正在扫描概念...</p>
            {scanProgress.totalConcepts > 0 && (
              <>
                <p className="text-sm text-gray-500 mt-2">
                  进度: {scanProgress.conceptsScanned}/{scanProgress.totalConcepts} ({Math.round(scanProgress.progress)}%)
                </p>
                {scanProgress.estimatedTime > 0 && (
                  <p className="text-sm text-gray-400 mt-1">
                    预估剩余: {formatScanTime(scanProgress.estimatedTime)}
                  </p>
                )}
                <div className="w-full bg-gray-200 rounded-full h-2 mt-4">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${scanProgress.progress}%` }}
                  />
                </div>
              </>
            )}
          </div>
        )}

        {/* Review State */}
        {panelState === 'review' && (
          <div>
            <div className="mb-4">
              <p className="text-sm text-gray-500">
                发现 <span className="font-semibold text-gray-700">{suggestions.length}</span> 条合并建议
              </p>
            </div>

            {suggestions.length === 0 ? (
              <div className="text-center py-8">
                <Check className="w-12 h-12 text-green-500 mx-auto mb-4" />
                <p className="text-gray-600">未发现重复概念</p>
              </div>
            ) : (
              <div className="space-y-3">
                {suggestions.map(suggestion => (
                  <div
                    key={suggestion.id}
                    className="border rounded-lg p-3 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start gap-2">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(suggestion.id)}
                        onChange={() => toggleSelection(suggestion.id)}
                        className="mt-1 w-4 h-4 rounded border-gray-300"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-sm">
                            {suggestion.source.text}
                          </span>
                          <span className="text-gray-400">→</span>
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-sm">
                            {suggestion.target.text}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-xs ${getConfidenceColor(suggestion.confidence)}`}>
                            {Math.round(suggestion.confidence * 100)}%
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          论文数: {suggestion.source.paper_count} → {suggestion.target.paper_count}
                        </p>
                        <p className="text-xs text-gray-600 mt-2 bg-gray-50 p-2 rounded">
                          {suggestion.rationale}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Executing State */}
        {panelState === 'executing' && (
          <div className="text-center py-12">
            <RefreshCw className="w-12 h-12 text-blue-500 mx-auto mb-4 animate-spin" />
            <p className="text-gray-600">正在执行合并...</p>
          </div>
        )}

        {/* Result State */}
        {panelState === 'result' && (
          <div>
            <div className="mb-4">
              <p className="text-sm text-gray-500">
                已完成 <span className="font-semibold text-green-600">{executeDetails.filter(d => d.status === 'success').length}</span> 项合并
              </p>
            </div>

            <div className="space-y-2">
              {executeDetails.map((detail, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg ${
                    detail.status === 'success'
                      ? 'bg-green-50 border border-green-200'
                      : 'bg-red-50 border border-red-200'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {detail.status === 'success' ? (
                      <Check className="w-4 h-4 text-green-500" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-red-500" />
                    )}
                    <span className="text-sm">
                      {detail.source} → {detail.target}
                    </span>
                  </div>
                  {detail.message && (
                    <p className="text-xs text-red-600 mt-1 ml-6">{detail.message}</p>
                  )}
                </div>
              ))}
            </div>

            <button
              onClick={handleReset}
              className="w-full mt-4 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            >
              重新扫描
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      {panelState === 'review' && suggestions.length > 0 && (
        <div className="p-4 border-t">
          <button
            onClick={handleExecute}
            disabled={selectedIds.size === 0}
            className={`w-full py-2 rounded-lg transition-colors ${
              selectedIds.size > 0
                ? 'bg-blue-500 text-white hover:bg-blue-600'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            执行选中的合并 ({selectedIds.size})
          </button>
        </div>
      )}
    </div>
  )
}