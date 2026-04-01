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

    // Poll every 2 seconds
    const interval = setInterval(poll, 2000)
    poll() // Initial poll

    return () => clearInterval(interval)
  }, [sessionId, onComplete])

  return (
    <div className="space-y-3 p-3 bg-gray-50 rounded-lg">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">深入研究进度</span>
        <span className="text-sm text-gray-500">{progress}%</span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-amber-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="space-y-2">
        {dimensions.map((dim) => (
          <div key={dim} className="flex items-center gap-2 text-sm">
            {completed.includes(dim) ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : (
              <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
            )}
            <span className={completed.includes(dim) ? 'text-gray-700' : 'text-gray-400'}>
              {dim}
            </span>
          </div>
        ))}
      </div>

      {status === 'completed' && (
        <div className="flex items-center gap-2 text-sm text-green-600 pt-2 border-t border-gray-200">
          <FileText className="w-4 h-4" />
          <span>研究完成，报告已生成</span>
        </div>
      )}
    </div>
  )
}