import { X, FileUp, Brain, Network, Search, Settings } from 'lucide-react'
import { useTranslation } from '../i18n'

interface Props {
  onClose: () => void
  onOpenLLMConfig: () => void
}

export default function OnboardingModal({ onClose, onOpenLLMConfig }: Props) {
  const { t } = useTranslation()

  const FEATURES = [
    {
      icon: FileUp,
      title: t.modal.onboarding.features.pdfUpload,
      description: t.modal.onboarding.features.pdfUploadDesc
    },
    {
      icon: Brain,
      title: t.modal.onboarding.features.conceptExtract,
      description: t.modal.onboarding.features.conceptExtractDesc
    },
    {
      icon: Network,
      title: t.modal.onboarding.features.graphInteract,
      description: t.modal.onboarding.features.graphInteractDesc
    },
    {
      icon: Search,
      title: t.modal.onboarding.features.researchDiscover,
      description: t.modal.onboarding.features.researchDiscoverDesc
    }
  ]

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
    <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50 p-4">
      <div className="modal-academic max-w-lg w-full animate-slide-up">
        {/* Header */}
        <div className="relative overflow-hidden">
          {/* Decorative background */}
          <div className="absolute inset-0 bg-gradient-amber opacity-10" />
          <div className="absolute inset-0 bg-paper-lines opacity-30" />

          <div className="relative p-6 text-center">
            <button
              onClick={handleClose}
              className="absolute top-4 right-4 w-8 h-8 rounded-soft text-muted hover:text-sepia hover:bg-paper flex items-center justify-center transition-all"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="w-16 h-16 mx-auto mb-4 rounded-large bg-gradient-amber flex items-center justify-center shadow-glow-amber">
              <span className="text-3xl">🎉</span>
            </div>

            <h2 className="font-display text-2xl text-sepia mb-2">
              {t.modal.onboarding.welcome}
            </h2>
            <p className="font-body text-muted">
              {t.modal.onboarding.demo}
            </p>
          </div>
        </div>

        {/* Features */}
        <div className="p-6">
          <div className="grid grid-cols-2 gap-3 mb-6">
            {FEATURES.map((feature, i) => (
              <div
                key={i}
                className="flex items-start gap-3 p-4 bg-paper rounded-large border border-academic"
              >
                <div className="w-9 h-9 rounded-medium bg-vellum border border-academic flex items-center justify-center flex-shrink-0">
                  <feature.icon className="w-4 h-4 text-sepia" />
                </div>
                <div>
                  <p className="font-display text-sm text-sepia">{feature.title}</p>
                  <p className="font-body text-xs text-muted mt-0.5">{feature.description}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Tip */}
          <div className="bg-amber/5 border border-amber/20 rounded-large p-4 mb-6">
            <p className="font-body text-sm text-sepia">
              💡 <strong>{t.modal.onboarding.tip}</strong>
            </p>
          </div>

          {/* Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleClose}
              className="btn-secondary flex-1"
            >
              {t.modal.close}
            </button>
            <button
              onClick={handleGoToSettings}
              className="btn-primary flex-1 flex items-center justify-center gap-2"
            >
              <Settings className="w-4 h-4" />
              {t.modal.goSettings}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}