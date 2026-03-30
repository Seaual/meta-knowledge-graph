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

  // Check first visit for onboarding
  useEffect(() => {
    const dismissed = localStorage.getItem('mkg_onboarding_dismissed')
    if (!dismissed) {
      setShowOnboarding(true)
    }
  }, [])

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="loading-academic">
          {t.common.loading}
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-6xl mx-auto animate-fade-in">
      {/* Hero Section */}
      <div className="mb-8">
        <h1 className="font-display text-3xl text-sepia mb-2">
          {t.home.title}
        </h1>
        <p className="font-quote text-lg text-muted italic">
          {t.home.subtitle}
        </p>
      </div>

      {/* Stats Grid - Elegant Card Design */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5 mb-8">
        <div className="card-stat animate-slide-up" style={{ animationDelay: '0ms' }}>
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-medium bg-gradient-amber flex items-center justify-center shadow-paper">
              <FileText className="w-5 h-5 text-vellum" />
            </div>
            <div>
              <p className="font-mono text-xs text-muted uppercase tracking-wider mb-1">{t.home.stats.papers}</p>
              <p className="font-display text-2xl text-sepia font-medium">{stats?.papers?.total || 0}</p>
            </div>
          </div>
        </div>

        <div className="card-stat animate-slide-up" style={{ animationDelay: '50ms' }}>
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-medium bg-gradient-sepia flex items-center justify-center shadow-paper">
              <GitBranch className="w-5 h-5 text-vellum" />
            </div>
            <div>
              <p className="font-mono text-xs text-muted uppercase tracking-wider mb-1">{t.home.stats.concepts}</p>
              <p className="font-display text-2xl text-sepia font-medium">{stats?.concepts?.total || 0}</p>
            </div>
          </div>
        </div>

        <div className="card-stat animate-slide-up" style={{ animationDelay: '100ms' }}>
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-medium bg-gradient-sepia flex items-center justify-center shadow-paper">
              <Network className="w-5 h-5 text-vellum" />
            </div>
            <div>
              <p className="font-mono text-xs text-muted uppercase tracking-wider mb-1">{t.home.stats.relations}</p>
              <p className="font-display text-2xl text-sepia font-medium">{stats?.relations || 0}</p>
            </div>
          </div>
        </div>

        <div className="card-stat animate-slide-up" style={{ animationDelay: '150ms' }}>
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-medium bg-gradient-amber flex items-center justify-center shadow-paper">
              <TrendingUp className="w-5 h-5 text-vellum" />
            </div>
            <div>
              <p className="font-mono text-xs text-muted uppercase tracking-wider mb-1">{t.home.stats.roots}</p>
              <p className="font-display text-2xl text-sepia font-medium">{stats?.root_concepts || 0}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions - Two Column Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-8">
        {/* Primary Actions */}
        <Link
          to="/papers"
          className="card-action group animate-slide-up"
          style={{ animationDelay: '200ms' }}
        >
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-large bg-vellum border border-academic flex items-center justify-center group-hover:bg-gradient-amber group-hover:border-transparent transition-all duration-300">
              <BookOpen className="w-6 h-6 text-sepia group-hover:text-vellum transition-colors" />
            </div>
            <div className="flex-1">
              <h3 className="font-display text-lg text-sepia mb-1">{t.home.actions.uploadPapers}</h3>
              <p className="font-body text-sm text-muted">{t.home.actions.uploadDesc}</p>
            </div>
            <div className="w-8 h-8 rounded-soft bg-paper flex items-center justify-center text-muted group-hover:bg-amber group-hover:text-vellum transition-all">
              <Layers className="w-4 h-4" />
            </div>
          </div>
        </Link>

        <Link
          to="/concepts"
          className="card-action group animate-slide-up"
          style={{ animationDelay: '250ms' }}
        >
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-large bg-vellum border border-academic flex items-center justify-center group-hover:bg-gradient-sepia group-hover:border-transparent transition-all duration-300">
              <GitBranch className="w-6 h-6 text-sepia group-hover:text-vellum transition-colors" />
            </div>
            <div className="flex-1">
              <h3 className="font-display text-lg text-sepia mb-1">{t.home.actions.exploreConcepts}</h3>
              <p className="font-body text-sm text-muted">{t.home.actions.exploreDesc}</p>
            </div>
            <div className="w-8 h-8 rounded-soft bg-paper flex items-center justify-center text-muted group-hover:bg-amber group-hover:text-vellum transition-all">
              <Network className="w-4 h-4" />
            </div>
          </div>
        </Link>
      </div>

      {/* Configuration Section */}
      <div className="section-academic animate-slide-up" style={{ animationDelay: '300ms' }}>
        <div className="flex items-center gap-3 mb-5">
          <Settings className="w-5 h-5 text-muted" />
          <h2 className="font-mono text-sm text-muted uppercase tracking-wider">{t.home.config}</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={() => setShowLLMModal(true)}
            className="card-action text-left"
          >
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-soft bg-paper flex items-center justify-center">
                <Settings className="w-5 h-5 text-muted" />
              </div>
              <div className="flex-1">
                <p className="font-body font-medium text-sepia">{t.home.llmProvider}</p>
                <p className="font-mono text-xs text-muted">{llmStatus}</p>
              </div>
            </div>
          </button>

          <button
            onClick={() => setShowS2Modal(true)}
            className="card-action text-left"
          >
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-soft bg-paper flex items-center justify-center">
                <Database className="w-5 h-5 text-muted" />
              </div>
              <div className="flex-1">
                <p className="font-body font-medium text-sepia">{t.home.semanticScholar}</p>
                <p className="font-mono text-xs text-muted">{s2Status}</p>
              </div>
            </div>
          </button>
        </div>
      </div>

      {/* Paper Status Section */}
      {stats?.papers && (
        <div className="section-academic mt-6 animate-slide-up" style={{ animationDelay: '350ms' }}>
          <div className="flex items-center gap-3 mb-5">
            <FileText className="w-5 h-5 text-muted" />
            <h2 className="font-mono text-sm text-muted uppercase tracking-wider">{t.home.processingStatus}</h2>
          </div>

          <div className="flex flex-wrap gap-4">
            {Object.entries(stats.papers)
              .filter(([k]) => k !== 'total')
              .map(([status, count]) => (
                <div
                  key={status}
                  className={`px-5 py-4 rounded-large border border-academic bg-vellum
                    ${status === 'processed' ? 'border-l-2 border-l-graph-technique' : ''}
                    ${status === 'pending' ? 'border-l-2 border-l-amber' : ''}
                    ${status === 'failed' ? 'border-l-2 border-l-status-error' : ''}
                  `}
                >
                  <p className="font-display text-xl text-sepia">{count}</p>
                  <p className="font-mono text-xs text-muted capitalize">{t.papers.status[status as keyof typeof t.papers.status] || status}</p>
                </div>
              ))}
          </div>
        </div>
      )}

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