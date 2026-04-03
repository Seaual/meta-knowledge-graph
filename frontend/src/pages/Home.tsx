import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText, GitBranch, Network, TrendingUp, Settings, Database, BookOpen, Layers } from 'lucide-react'
import { graphApi, llmApi, s2Api } from '../lib/api'
import LLMConfigModal from '../components/LLMConfigModal'
import S2ConfigModal from '../components/S2ConfigModal'
import OnboardingModal from '../components/OnboardingModal'
import { useTranslation } from '../i18n'

interface Stats {
  papers: { total: number; [key: string]: number }
  concepts: { total: number }
  relations: number
  root_concepts: number
}

// Animated counter component
function AnimatedNumber({ value, duration = 600 }: { value: number; duration?: number }) {
  const [displayValue, setDisplayValue] = useState(0)

  useEffect(() => {
    const startTime = Date.now()
    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplayValue(Math.floor(eased * value))
      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }
    requestAnimationFrame(animate)
  }, [value, duration])

  return <span>{displayValue.toLocaleString()}</span>
}

export default function Home() {
  const { t } = useTranslation()
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [llmStatus, setLlmStatus] = useState<string>('')
  const [showLLMModal, setShowLLMModal] = useState(false)
  const [s2Status, setS2Status] = useState<string>('')
  const [showS2Modal, setShowS2Modal] = useState(false)
  const [showOnboarding, setShowOnboarding] = useState(false)

  useEffect(() => {
    graphApi.stats().then(res => {
      setStats(res.data)
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    llmApi.getConfig().then(res => {
      const config = res.data
      if (config.providers && config.providers.length > 0) {
        const p = config.providers[0]
        setLlmStatus(`${p.provider} (${p.model || 'default'})`)
      } else {
        setLlmStatus(t.home.notConfigured)
      }
    }).catch(() => setLlmStatus(t.home.notConfigured))
  }, [t.home.notConfigured])

  useEffect(() => {
    s2Api.getConfig().then(res => {
      if (res.data.has_api_key) {
        setS2Status(res.data.enabled ? t.home.enabled : t.home.disabled)
      } else {
        setS2Status(t.home.notConfigured)
      }
    }).catch(() => setS2Status(t.home.notConfigured))
  }, [t.home.enabled, t.home.disabled, t.home.notConfigured])

  useEffect(() => {
    const dismissed = localStorage.getItem('mkg_onboarding_dismissed')
    if (!dismissed) {
      setShowOnboarding(true)
    }
  }, [])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="flex gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[var(--color-accent)] animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 rounded-full bg-[var(--color-accent)] animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 rounded-full bg-[var(--color-accent)] animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-8 max-w-5xl mx-auto animate-fade-in">
        {/* Hero */}
        <header className="mb-10">
          <h1 className="font-display text-2xl mb-1 animate-number" style={{ color: 'var(--color-ink)' }}>
            {t.home.title}
          </h1>
          <p className="text-secondary animate-slide-right" style={{ fontSize: '0.9375rem', animationDelay: '100ms' }}>
            {t.home.subtitle}
          </p>
        </header>

        {/* Stats */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10 stagger-children">
          {[
            { icon: FileText, label: t.home.stats.papers, value: stats?.papers?.total || 0 },
            { icon: GitBranch, label: t.home.stats.concepts, value: stats?.concepts?.total || 0 },
            { icon: Network, label: t.home.stats.relations, value: stats?.relations || 0 },
            { icon: TrendingUp, label: t.home.stats.roots, value: stats?.root_concepts || 0 },
          ].map((stat, i) => (
            <div
              key={i}
              className="card-stat group"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <div className="flex items-center gap-3 mb-2">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ background: 'var(--color-overlay)' }}
                >
                  <stat.icon className="w-4 h-4" style={{ color: 'var(--color-accent)' }} />
                </div>
                <span className="font-mono text-xs uppercase tracking-wider text-muted">
                  {stat.label}
                </span>
              </div>
              <p className="font-display text-2xl font-medium" style={{ color: 'var(--color-ink)' }}>
                <AnimatedNumber value={stat.value} />
              </p>
            </div>
          ))}
        </section>

        {/* Actions */}
        <section className="grid md:grid-cols-2 gap-4 mb-10">
          <Link
            to="/papers"
            className="card-action group block"
          >
            <div className="flex items-center gap-4">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center transition-all"
                style={{
                  background: 'var(--color-overlay)',
                }}
              >
                <BookOpen className="w-5 h-5" style={{ color: 'var(--color-accent)' }} />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-body font-medium text-sm mb-0.5" style={{ color: 'var(--color-ink)' }}>
                  {t.home.actions.uploadPapers}
                </h3>
                <p className="text-xs text-muted truncate">{t.home.actions.uploadDesc}</p>
              </div>
              <Layers className="w-4 h-4 text-muted group-hover:text-accent transition-colors" />
            </div>
          </Link>

          <Link
            to="/concepts"
            className="card-action group block"
          >
            <div className="flex items-center gap-4">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center"
                style={{ background: 'var(--color-overlay)' }}
              >
                <Network className="w-5 h-5" style={{ color: 'var(--color-accent)' }} />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-body font-medium text-sm mb-0.5" style={{ color: 'var(--color-ink)' }}>
                  {t.home.actions.exploreConcepts}
                </h3>
                <p className="text-xs text-muted truncate">{t.home.actions.exploreDesc}</p>
              </div>
              <GitBranch className="w-4 h-4 text-muted group-hover:text-accent transition-colors" />
            </div>
          </Link>
        </section>

        {/* Configuration */}
        <section className="section mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Settings className="w-4 h-4 text-muted" />
            <h2 className="font-mono text-xs uppercase tracking-wider text-muted">
              {t.home.config}
            </h2>
          </div>

          <div className="grid md:grid-cols-2 gap-3">
            <button
              onClick={() => setShowLLMModal(true)}
              className="card-action text-left"
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center"
                  style={{ background: 'var(--color-overlay)' }}
                >
                  <Settings className="w-4 h-4 text-muted" />
                </div>
                <div>
                  <p className="font-body font-medium text-sm" style={{ color: 'var(--color-ink)' }}>
                    {t.home.llmProvider}
                  </p>
                  <p className="font-mono text-xs text-muted">{llmStatus}</p>
                </div>
              </div>
            </button>

            <button
              onClick={() => setShowS2Modal(true)}
              className="card-action text-left"
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center"
                  style={{ background: 'var(--color-overlay)' }}
                >
                  <Database className="w-4 h-4 text-muted" />
                </div>
                <div>
                  <p className="font-body font-medium text-sm" style={{ color: 'var(--color-ink)' }}>
                    {t.home.semanticScholar}
                  </p>
                  <p className="font-mono text-xs text-muted">{s2Status}</p>
                </div>
              </div>
            </button>
          </div>
        </section>

        {/* Processing Status */}
        {stats?.papers && (
          <section className="section">
            <div className="flex items-center gap-2 mb-4">
              <FileText className="w-4 h-4 text-muted" />
              <h2 className="font-mono text-xs uppercase tracking-wider text-muted">
                {t.home.processingStatus}
              </h2>
            </div>

            <div className="flex flex-wrap gap-3">
              {Object.entries(stats.papers)
                .filter(([k]) => k !== 'total')
                .map(([status, count]) => (
                  <div
                    key={status}
                    className="px-4 py-3 rounded-lg"
                    style={{
                      background: 'var(--color-overlay)',
                      borderLeft: `3px solid ${
                        status === 'processed' ? 'var(--color-accent)' :
                        status === 'pending' ? 'var(--color-highlight)' :
                        '#b43c3c'
                      }`
                    }}
                  >
                    <p className="font-display text-lg font-medium" style={{ color: 'var(--color-ink)' }}>
                      <AnimatedNumber value={count as number} />
                    </p>
                    <p className="font-mono text-xs text-muted capitalize">
                      {t.papers.status[status as keyof typeof t.papers.status] || status}
                    </p>
                  </div>
                ))}
            </div>
          </section>
        )}
      </div>

      {/* Modals */}
      {showLLMModal && (
        <LLMConfigModal
          onClose={() => setShowLLMModal(false)}
          onSave={() => {
            setShowLLMModal(false)
            llmApi.getConfig().then(res => {
              const config = res.data
              if (config.providers && config.providers.length > 0) {
                const p = config.providers[0]
                setLlmStatus(`${p.provider} (${p.model || 'default'})`)
              }
            })
          }}
        />
      )}

      {showS2Modal && (
        <S2ConfigModal
          onClose={() => setShowS2Modal(false)}
          onSave={() => {
            setShowS2Modal(false)
            s2Api.getConfig().then(res => {
              if (res.data.has_api_key) {
                setS2Status(res.data.enabled ? t.home.enabled : t.home.disabled)
              } else {
                setS2Status(t.home.notConfigured)
              }
            })
          }}
        />
      )}

      {showOnboarding && (
        <OnboardingModal
          onClose={() => setShowOnboarding(false)}
          onOpenLLMConfig={() => setShowLLMModal(true)}
        />
      )}
    </div>
  )
}