import { lazy, Suspense, Component, ReactNode } from 'react'

// 错误边界组件
class AttachmentErrorBoundary extends Component<
  { children: ReactNode; type: string },
  { hasError: boolean; error: string }
> {
  state = { hasError: false, error: '' }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="my-2 p-4 rounded-xl"
          style={{
            background: 'rgba(180, 60, 60, 0.05)',
            border: '1px solid rgba(180, 60, 60, 0.2)',
            color: '#8b4040',
          }}
        >
          <p className="font-body text-sm mb-1">{this.props.type} 附件渲染出错</p>
          <p className="font-mono text-xs opacity-70">{this.state.error}</p>
        </div>
      )
    }
    return this.props.children
  }
}

// Lazy load 卡片组件
const ResearchPointsCard = lazy(() => import('./cards/ResearchPointsCard'))
const PaperDetailCard = lazy(() => import('./cards/PaperDetailCard'))
const PaperListCard = lazy(() => import('./cards/PaperListCard'))
const RecommendationCard = lazy(() => import('./cards/RecommendationCard'))
const CitationAnalysisCard = lazy(() => import('./cards/CitationAnalysisCard'))
const DeepResearchCard = lazy(() => import('./cards/DeepResearchCard'))
const ConceptGraphInChat = lazy(() => import('./ConceptGraphInChat'))

interface ChatAttachment {
  type: string
  data: any
}

interface Props {
  attachments: ChatAttachment[]
  onSendMessage: (text: string) => void
}

function CardFallback() {
  return (
    <div
      className="my-2 p-4 rounded-xl animate-pulse"
      style={{ background: 'rgba(184, 134, 11, 0.04)', height: 80 }}
    />
  )
}

export default function ChatAttachments({ attachments, onSendMessage }: Props) {
  if (!attachments || attachments.length === 0) return null

  const knownTypes = ['research_points', 'paper_detail', 'paper_list', 'concept_graph', 'recommendation', 'citation_analysis', 'deep_research']

  return (
    <div className="chat-attachments space-y-3 mt-2">
      {attachments
        .filter((att) => knownTypes.includes(att.type))
        .map((att, i) => (
          <AttachmentErrorBoundary key={`${att.type}-${i}`} type={att.type}>
            <Suspense fallback={<CardFallback />}>
              {att.type === 'research_points' && att.data && (
                <ResearchPointsCard data={att.data} onAction={onSendMessage} />
              )}
              {att.type === 'paper_detail' && att.data && (
                <PaperDetailCard data={att.data} />
              )}
              {att.type === 'paper_list' && att.data && (
                <PaperListCard data={att.data} onAction={onSendMessage} />
              )}
              {att.type === 'concept_graph' && att.data && (
                <ConceptGraphInChat data={att.data} />
              )}
              {att.type === 'recommendation' && att.data && (
                <RecommendationCard data={att.data} onAction={onSendMessage} />
              )}
              {att.type === 'citation_analysis' && att.data && (
                <CitationAnalysisCard data={att.data} />
              )}
              {att.type === 'deep_research' && att.data && (
                <DeepResearchCard data={att.data} onAction={onSendMessage} />
              )}
            </Suspense>
          </AttachmentErrorBoundary>
        ))}
    </div>
  )
}