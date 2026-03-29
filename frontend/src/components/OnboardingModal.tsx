import { X, FileUp, Brain, Network, Search, Settings } from 'lucide-react'

interface Props {
  onClose: () => void
  onOpenLLMConfig: () => void
}

const FEATURES = [
  {
    icon: FileUp,
    title: 'PDF 上传',
    description: '上传论文 PDF，自动提取元数据'
  },
  {
    icon: Brain,
    title: '概念提取',
    description: 'LLM 自动构建概念层级'
  },
  {
    icon: Network,
    title: '图谱交互',
    description: '拖拽、缩放、点击探索关系'
  },
  {
    icon: Search,
    title: '研究点发现',
    description: '基于图谱结构发现潜在研究方向'
  }
]

export default function OnboardingModal({ onClose, onOpenLLMConfig }: Props) {
  const handleClose = () => {
    localStorage.setItem('mkg_onboarding_dismissed', 'true')
    onClose()
  }

  const handleGoToSettings = () => {
    localStorage.setItem('mkg_onboarding_dismissed', 'true')
    onClose()
    onOpenLLMConfig()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden">
        {/* Header */}
        <div className="bg-brand-gradient p-6 text-center relative">
          <button
            onClick={handleClose}
            className="absolute top-4 right-4 text-white/70 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
          <div className="text-4xl mb-2">🎉</div>
          <h2 className="text-xl font-bold text-white">欢迎使用 Meta Knowledge Graph</h2>
          <p className="text-white/80 text-sm mt-2">
            这是一个演示图谱，包含 10 篇 LLM 经典论文
          </p>
        </div>

        {/* Features */}
        <div className="p-6">
          <div className="grid grid-cols-2 gap-4 mb-6">
            {FEATURES.map((feature, i) => (
              <div
                key={i}
                className="flex items-start gap-3 p-3 bg-brand-fill rounded-xl"
              >
                <div className="h-8 w-8 bg-brand-button rounded-lg flex items-center justify-center flex-shrink-0">
                  <feature.icon className="h-4 w-4 text-white" />
                </div>
                <div>
                  <p className="font-medium text-brand-700 text-sm">{feature.title}</p>
                  <p className="text-xs text-brand-500 mt-0.5">{feature.description}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Tip */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
            <p className="text-sm text-amber-800">
              💡 <strong>提示：</strong>要处理你自己的论文，请先在设置页面配置 LLM API Key
            </p>
          </div>

          {/* Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleClose}
              className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl text-gray-700 hover:bg-gray-50 transition-colors"
            >
              关闭
            </button>
            <button
              onClick={handleGoToSettings}
              className="flex-1 px-4 py-2.5 bg-brand-button text-white rounded-xl hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
            >
              <Settings className="h-4 w-4" />
              前往设置
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}