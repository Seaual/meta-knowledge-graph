import { lazy, Suspense } from 'react'

// Lazy load 卡片组件
const ResearchPointsCard = lazy(() => import('./cards/ResearchPointsCard'))
const PaperDetailCard = lazy(() => import('./cards/PaperDetailCard'))
const PaperListCard = lazy(() => import('./cards/PaperListCard'))
const RecommendationCard = lazy(() => import('./cards/RecommendationCard'))
const CitationAnalysisCard = lazy(() => import('./cards/CitationAnalysisCard'))
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

  const knownTypes = ['research_points', 'paper_detail', 'paper_list', 'concept_graph', 'recommendation', 'citation_analysis']

  return (
    <div className="chat-attachments space-y-3 mt-2">
      {attachments
        .filter((att) => knownTypes.includes(att.type))
        .map((att, i) => (
          <Suspense key={`${att.type}-${i}`} fallback={<CardFallback />}>
            {att.type === 'research_points' && (
              <ResearchPointsCard data={att.data} onAction={onSendMessage} />
            )}
            {att.type === 'paper_detail' && (
              <PaperDetailCard data={att.data} />
            )}
            {att.type === 'paper_list' && (
              <PaperListCard data={att.data} onAction={onSendMessage} />
            )}
            {att.type === 'concept_graph' && (
              <ConceptGraphInChat data={att.data} />
            )}
            {att.type === 'recommendation' && (
              <RecommendationCard data={att.data} onAction={onSendMessage} />
            )}
            {att.type === 'citation_analysis' && (
              <CitationAnalysisCard data={att.data} />
            )}
          </Suspense>
        ))}
    </div>
  )
}