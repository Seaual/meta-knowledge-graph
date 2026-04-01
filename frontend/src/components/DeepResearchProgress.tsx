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
        fontFamily: '"Source Sans 3", system-ui, sans-serif',
        background: 'rgba(245, 240, 232, 0.8)',
        border: '1px solid rgba(184, 134, 11, 0.15)',
      }}
    >
      {/* 进度标题 */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-academic-amber animate-pulse" />
          <span className="text-xs font-medium text-academic-sepia">深入研究进度</span>
        </div>
        <span className="text-xs font-mono text-academic-muted">{progress}%</span>
      </div>

      {/* 进度条 */}
      <div
        className="w-full h-1.5 rounded-full overflow-hidden"
        style={{ background: 'rgba(184, 134, 11, 0.1)' }}
      >
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${progress}%`,
            background: 'linear-gradient(90deg, #b8860b 0%, #d4a012 100%)',
            boxShadow: progress > 0 ? '0 0 8px rgba(184, 134, 11, 0.4)' : 'none',
          }}
        />
      </div>

      {/* 维度列表 */}
      <div className="mt-3 space-y-1.5">
        {dimensions.map((dim, i) => (
          <div
            key={dim}
            className="flex items-center gap-2 text-xs py-1 px-2 rounded-soft transition-all"
            style={{
              animationDelay: `${i * 100}ms`,
              background: completed.includes(dim) ? 'rgba(45, 90, 39, 0.05)' : 'transparent',
            }}
          >
            {completed.includes(dim) ? (
              <CheckCircle className="w-3.5 h-3.5 text-status-success" />
            ) : (
              <Loader2 className="w-3.5 h-3.5 text-academic-amber animate-spin" />
            )}
            <span
              className={completed.includes(dim) ? 'text-academic-ink' : 'text-academic-muted'}
            >
              {dim}
            </span>
            {completed.includes(dim) && (
              <span className="ml-auto text-[10px] font-mono text-status-success">✓</span>
            )}
          </div>
        ))}
      </div>

      {/* 完成状态 */}
      {status === 'completed' && (
        <div
          className="flex items-center gap-2 text-xs pt-2 mt-2"
          style={{
            borderTop: '1px solid rgba(184, 134, 11, 0.1)',
            color: '#2d5a27',
          }}
        >
          <FileText className="w-3.5 h-3.5" />
          <span className="font-medium">研究完成，报告已生成</span>
        </div>
      )}
    </div>
  )
}