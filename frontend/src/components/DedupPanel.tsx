import { useState, useEffect, useRef } from 'react'
import { X, RefreshCw, Check, AlertCircle, Merge } from 'lucide-react'
import { dedupApi } from '../lib/api'
import { useTranslation } from '../i18n'

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
  phase: 'prefiltering' | 'analyzing' | 'completed' | 'failed' | 'unknown'
  totalConcepts: number
  conceptsScanned: number
  batchesTotal: number
  batchesCompleted: number
  filteredCount: number
  highConfidenceCount: number
  progress: number
  estimatedTime: number
}

interface DedupPanelProps {
  isOpen: boolean
  onClose: () => void
  folderId?: string
}

export default function DedupPanel({ isOpen, onClose, folderId = 'default' }: DedupPanelProps) {
  const { t } = useTranslation()
  const [panelState, setPanelState] = useState<PanelState>('idle')
  const [scanId, setScanId] = useState<string>('')
  const [suggestions, setSuggestions] = useState<MergeSuggestion[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [executeDetails, setExecuteDetails] = useState<ExecuteDetail[]>([])
  const [floatingFixed, setFloatingFixed] = useState(0)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_floatingDetails, setFloatingDetails] = useState<Array<{concept: string; parent?: string; status: string}>>([])
  const [error, setError] = useState<string | null>(null)
  const [scanProgress, setScanProgress] = useState<ScanProgress>({
    scanId: null,
    phase: 'unknown',
    totalConcepts: 0,
    conceptsScanned: 0,
    batchesTotal: 0,
    batchesCompleted: 0,
    filteredCount: 0,
    highConfidenceCount: 0,
    progress: 0,
    estimatedTime: 0
  })
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const handleScan = async () => {
    setPanelState('scanning')
    setError(null)
    setScanProgress({
      scanId: null,
      phase: 'unknown',
      totalConcepts: 0,
      conceptsScanned: 0,
      batchesTotal: 0,
      batchesCompleted: 0,
      filteredCount: 0,
      highConfidenceCount: 0,
      progress: 0,
      estimatedTime: 0
    })

    try {
      const res = await dedupApi.scan(folderId)
      const newScanId = res.data.scan_id

      setScanId(newScanId)
      setScanProgress(prev => ({
        ...prev,
        scanId: newScanId,
        totalConcepts: res.data.total_concepts
      }))

      startPolling(newScanId)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start scan')
      setPanelState('idle')
    }
  }

  const startPolling = (scanId: string) => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
    }

    pollingRef.current = setInterval(async () => {
      try {
        const res = await dedupApi.scanStatus(scanId)
        const data = res.data

        setScanProgress({
          scanId,
          phase: data.phase || 'unknown',
          totalConcepts: data.total_concepts,
          conceptsScanned: data.concepts_scanned,
          batchesTotal: data.batches_total || 0,
          batchesCompleted: data.batches_completed || 0,
          filteredCount: data.filtered_count || 0,
          highConfidenceCount: data.high_confidence_count || 0,
          progress: data.progress,
          estimatedTime: data.estimated_time
        })

        if (data.status === 'completed') {
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
          setError(data.error || 'Scan failed')
          setPanelState('idle')
        }
      } catch (err: any) {
        console.error('Poll error:', err)
        setError('Failed to get scan status, check network connection')
      }
    }, 1000)
  }

  const handleExecute = async () => {
    setPanelState('executing')
    setError(null)
    try {
      const res = await dedupApi.execute(scanId, Array.from(selectedIds))
      setExecuteDetails(res.data.details)
      setFloatingFixed(res.data.floating_fixed || 0)
      setFloatingDetails(res.data.floating_details || [])
      setPanelState('result')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Execution failed')
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
    setFloatingFixed(0)
    setFloatingDetails([])
    setError(null)
    setScanProgress({
      scanId: null,
      phase: 'unknown',
      totalConcepts: 0,
      conceptsScanned: 0,
      batchesTotal: 0,
      batchesCompleted: 0,
      filteredCount: 0,
      highConfidenceCount: 0,
      progress: 0,
      estimatedTime: 0
    })
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }

  const getConfidenceStyle = (confidence: number) => {
    if (confidence >= 0.9) return { bg: '#2d5a2715', color: '#2d5a27', border: '#2d5a2730' }
    if (confidence >= 0.7) return { bg: '#b8860b15', color: '#b8860b', border: '#b8860b30' }
    return { bg: '#a89a8a15', color: '#8a7a6a', border: '#a89a8a30' }
  }

  const formatScanTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    if (minutes < 60) return `${minutes}m${secs > 0 ? secs + 's' : ''}`
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return `${hours}h${mins > 0 ? mins + 'm' : ''}`
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
    <div className="fixed inset-y-0 right-0 w-96 card-academic shadow-modal z-50 flex flex-col animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between p-5 border-b border-academic bg-vellum">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-medium bg-gradient-sepia flex items-center justify-center">
            <Merge className="w-5 h-5 text-vellum" />
          </div>
          <h2 className="font-display text-lg text-sepia font-medium">{t.dedup.title}</h2>
        </div>
        <button
          onClick={onClose}
          className="w-8 h-8 rounded-soft text-muted hover:text-sepia hover:bg-paper flex items-center justify-center transition-all"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5">
        {/* Error */}
        {error && (
          <div className="mb-4 p-3 bg-status-error/5 border border-status-error/20 rounded-large flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-status-error flex-shrink-0 mt-0.5" />
            <p className="font-body text-sm text-status-error">{error}</p>
          </div>
        )}

        {/* Idle State */}
        {panelState === 'idle' && (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-large bg-paper border border-academic flex items-center justify-center">
              <Merge className="w-8 h-8 text-muted" />
            </div>
            <p className="font-body text-muted mb-6">{t.dedup.scanning}</p>
            <button onClick={handleScan} className="btn-primary">
              {t.dedup.scan}
            </button>
          </div>
        )}

        {/* Scanning State */}
        {panelState === 'scanning' && (
          <div className="text-center py-12">
            <RefreshCw className="w-12 h-12 text-sepia mx-auto mb-4 animate-spin" />
            {scanProgress.phase === 'prefiltering' ? (
              <p className="font-body text-sepia">{t.dedup.prefiltering}</p>
            ) : (
              <>
                <p className="font-body text-sepia">{t.dedup.analyzing}</p>
                {scanProgress.batchesTotal > 0 && (
                  <p className="font-mono text-sm text-muted mt-1">
                    {t.dedup.batch}: {scanProgress.batchesCompleted}/{scanProgress.batchesTotal}
                  </p>
                )}
              </>
            )}
            {scanProgress.totalConcepts > 0 && (
              <>
                <p className="font-mono text-sm text-muted mt-2">
                  {t.dedup.progress}: {scanProgress.conceptsScanned}/{scanProgress.totalConcepts} ({Math.round(scanProgress.progress)}%)
                </p>
                {scanProgress.estimatedTime > 0 && (
                  <p className="font-mono text-xs text-faint mt-1">
                    {t.dedup.estimatedTime}: {formatScanTime(scanProgress.estimatedTime)}
                  </p>
                )}
                <div className="w-full bg-paper rounded-full h-2 mt-4">
                  <div
                    className="bg-gradient-amber h-2 rounded-full transition-all"
                    style={{ width: `${scanProgress.progress}%` }}
                  />
                </div>
                {scanProgress.highConfidenceCount > 0 && (
                  <p className="font-mono text-sm text-status-success mt-2">
                    {scanProgress.highConfidenceCount} {t.dedup.highConfidence}
                  </p>
                )}
              </>
            )}
          </div>
        )}

        {/* Review State */}
        {panelState === 'review' && (
          <div>
            <div className="mb-4">
              <p className="font-body text-sm text-muted">
                {t.dedup.foundSuggestions} <span className="font-display font-medium text-sepia">{suggestions.length}</span> {t.dedup.mergeSuggestions}
              </p>
            </div>

            {suggestions.length === 0 ? (
              <div className="text-center py-8">
                <div className="w-12 h-12 mx-auto mb-4 rounded-large bg-status-success/10 flex items-center justify-center">
                  <Check className="w-6 h-6 text-status-success" />
                </div>
                <p className="font-body text-sepia">{t.dedup.noDuplicates}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {suggestions.map(suggestion => {
                  const confStyle = getConfidenceStyle(suggestion.confidence)
                  return (
                    <div
                      key={suggestion.id}
                      className="border border-academic rounded-large p-3 hover:bg-vellum/50 transition-colors"
                    >
                      <div className="flex items-start gap-2">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(suggestion.id)}
                          onChange={() => toggleSelection(suggestion.id)}
                          className="mt-1 w-4 h-4 rounded border-academic accent-sepia"
                        />
                        <div className="flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span
                              className="badge-academic"
                              style={{ backgroundColor: '#a33b3b15', color: '#a33b3b', borderColor: '#a33b3b30' }}
                            >
                              {suggestion.source.text}
                            </span>
                            <span className="font-body text-muted">→</span>
                            <span
                              className="badge-academic"
                              style={{ backgroundColor: '#2d5a2715', color: '#2d5a27', borderColor: '#2d5a2730' }}
                            >
                              {suggestion.target.text}
                            </span>
                            <span
                              className="badge-academic text-xs"
                              style={{ backgroundColor: confStyle.bg, color: confStyle.color, borderColor: confStyle.border }}
                            >
                              {Math.round(suggestion.confidence * 100)}%
                            </span>
                          </div>
                          <p className="font-mono text-xs text-muted mt-1">
                            {t.dedup.papers}: {suggestion.source.paper_count} → {suggestion.target.paper_count}
                          </p>
                          <p className="font-body text-xs text-sepia mt-2 bg-paper p-2 rounded-medium">
                            {suggestion.rationale}
                          </p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* Executing State */}
        {panelState === 'executing' && (
          <div className="text-center py-12">
            <RefreshCw className="w-12 h-12 text-sepia mx-auto mb-4 animate-spin" />
            <p className="font-body text-sepia">{t.dedup.executing}</p>
          </div>
        )}

        {/* Result State */}
        {panelState === 'result' && (
          <div>
            <div className="mb-4">
              <p className="font-body text-sm text-muted">
                {t.dedup.completed} <span className="font-display font-medium text-status-success">{executeDetails.filter(d => d.status === 'success').length}</span> {t.dedup.merges}
                {floatingFixed > 0 && (
                  <span className="ml-2">
                    , {t.dedup.fixedFloating} <span className="font-display font-medium text-status-info">{floatingFixed}</span> {t.dedup.floatingConcepts}
                  </span>
                )}
              </p>
            </div>

            <div className="space-y-2">
              {executeDetails.map((detail, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-large ${
                    detail.status === 'success'
                      ? 'bg-status-success/5 border border-status-success/20'
                      : 'bg-status-error/5 border border-status-error/20'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {detail.status === 'success' ? (
                      <Check className="w-4 h-4 text-status-success" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-status-error" />
                    )}
                    <span className="font-body text-sm text-sepia">
                      {detail.source} → {detail.target}
                    </span>
                  </div>
                  {detail.message && (
                    <p className="font-mono text-xs text-status-error mt-1 ml-6">{detail.message}</p>
                  )}
                </div>
              ))}
            </div>

            <button onClick={handleReset} className="btn-secondary w-full mt-4">
              {t.dedup.scanAgain}
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      {panelState === 'review' && suggestions.length > 0 && (
        <div className="p-4 border-t border-academic bg-paper/50">
          <button
            onClick={handleExecute}
            disabled={selectedIds.size === 0}
            className={`w-full ${selectedIds.size > 0 ? 'btn-primary' : 'btn-secondary opacity-50 cursor-not-allowed'}`}
          >
            {t.dedup.executeSelected} ({selectedIds.size})
          </button>
        </div>
      )}
    </div>
  )
}