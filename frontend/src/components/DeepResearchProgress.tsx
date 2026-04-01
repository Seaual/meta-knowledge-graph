// frontend/src/components/DeepResearchProgress.tsx
import { useEffect, useState } from 'react'
import { Loader2, CheckCircle, FileText } from 'lucide-react'
import { agentApi } from '../lib/api'

interface ProgressProps {
  sessionId: string
  onComplete: (report: string) => void
}

export function DeepResearchProgress({ sessionId, onComplete }: ProgressProps) {
  const [status, setStatus] = useState<string>('pending')
  const [progress, setProgress] = useState(0)
  const [dimensions, setDimensions] = useState<string[]>([])
  const [completed, setCompleted] = useState<string[]>([])

  useEffect(() => {
    const poll = async () => {
      try {
        const result = await agentApi.getResearchStatus(sessionId)
        setStatus(result.status)
        setProgress(result.progress)
        setDimensions(result.dimensions)
        setCompleted(result.completedDimensions)

        if (result.status === 'completed') {
          const report = await agentApi.getResearchReport(sessionId)
          onComplete(report.report)
        }
      } catch (e) {
        console.error('Poll error:', e)
      }
    }

    const interval = setInterval(poll, 2000)
    poll()

    return () => clearInterval(interval)
  }, [sessionId, onComplete])

  return (
    <div
      className="p-3 rounded-medium animate-fade-in"
      style={{
        fontFamily: 'var(--font-body)',
        background: 'rgba(245, 240, 232, 0.01)',
        border: '1px solid rgba(184, 134, 11, 0.06)',
      }}
    >
      {/* 进度标题 */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: 'var(--color-amber)' }} />
          <span className="text-xs font-medium" style={{ color: 'var(--color-sepia)' }}>深入研究进度</span>
        </div>
        <span className="text-xs font-mono" style={{ color: 'var(--color-muted)' }}>{progress}%</span>
      </div>

      {/* 进度条 */}
      <div
        className="w-full h-1 rounded-full overflow-hidden"
        style={{ background: 'rgba(184, 134, 11, 0.04)' }}
      >
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${progress}%`,
            background: 'linear-gradient(90deg, #b8860b 0%, #d4a012 100%)',
            boxShadow: progress > 0 ? '0 0 8px rgba(184, 134, 11, 0.15)' : 'none',
          }}
        />
      </div>

      {/* 维度列表 */}
      <div className="mt-2 space-y-1">
        {dimensions.map((dim, i) => (
          <div
            key={dim}
            className="flex items-center gap-2 text-xs py-0.5 px-2 rounded-soft transition-all"
            style={{
              animationDelay: `${i * 100}ms`,
              background: completed.includes(dim) ? 'rgba(45, 90, 39, 0.03)' : 'transparent',
            }}
          >
            {completed.includes(dim) ? (
              <CheckCircle className="w-3 h-3" style={{ color: '#2d5a27' }} />
            ) : (
              <Loader2 className="w-3 h-3 animate-spin" style={{ color: 'var(--color-amber)' }} />
            )}
            <span style={{ color: completed.includes(dim) ? 'var(--color-ink)' : 'var(--color-muted)' }}>
              {dim}
            </span>
            {completed.includes(dim) && (
              <span className="ml-auto text-[10px] font-mono" style={{ color: '#2d5a27' }}>✓</span>
            )}
          </div>
        ))}
      </div>

      {/* 完成状态 */}
      {status === 'completed' && (
        <div
          className="flex items-center gap-1.5 text-xs pt-2 mt-2"
          style={{
            borderTop: '1px solid rgba(184, 134, 11, 0.04)',
            color: '#2d5a27',
          }}
        >
          <FileText className="w-3 h-3" />
          <span className="font-medium">研究完成</span>
        </div>
      )}
    </div>
  )
}