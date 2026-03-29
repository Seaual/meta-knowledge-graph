import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText, GitBranch, Network, TrendingUp, Settings, Database } from 'lucide-react'
import { graphApi, llmApi, s2Api } from '../lib/api'
import LLMConfigModal from '../components/LLMConfigModal'
import S2ConfigModal from '../components/S2ConfigModal'
import OnboardingModal from '../components/OnboardingModal'

interface Stats {
  papers: { total: number; [key: string]: number }
  concepts: { total: number }
  relations: number
  root_concepts: number
}

export default function Home() {
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
        setLlmStatus('未配置')
      }
    }).catch(() => setLlmStatus('未配置'))
  }, [])

  useEffect(() => {
    s2Api.getConfig().then(res => {
      if (res.data.has_api_key) {
        setS2Status(res.data.enabled ? '已启用' : '已禁用')
      } else {
        setS2Status('未配置')
      }
    }).catch(() => setS2Status('未配置'))
  }, [])

  // Check first visit for onboarding
  useEffect(() => {
    const dismissed = localStorage.getItem('mkg_onboarding_dismissed')
    if (!dismissed) {
      setShowOnboarding(true)
    }
  }, [])

  if (loading) {
    return <div className="text-center py-12">加载中...</div>
  }

  return (
    <div className="space-y-8 p-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-brand-gradient rounded-2xl shadow-brand p-6 border border-brand">
          <div className="flex items-center">
            <div className="h-11 w-11 bg-brand-button rounded-xl flex items-center justify-center">
              <FileText className="h-5 w-5 text-white" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-brand-500 font-medium">论文总数</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.papers?.total || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-brand-gradient rounded-2xl shadow-brand p-6 border border-brand">
          <div className="flex items-center">
            <div className="h-11 w-11 bg-brand-button rounded-xl flex items-center justify-center">
              <GitBranch className="h-5 w-5 text-white" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-brand-500 font-medium">概念总数</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.concepts?.total || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-brand-gradient rounded-2xl shadow-brand p-6 border border-brand">
          <div className="flex items-center">
            <div className="h-11 w-11 bg-brand-button rounded-xl flex items-center justify-center">
              <Network className="h-5 w-5 text-white" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-brand-500 font-medium">层级关系</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.relations || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-brand-gradient rounded-2xl shadow-brand p-6 border border-brand">
          <div className="flex items-center">
            <div className="h-11 w-11 bg-brand-button rounded-xl flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-white" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-brand-500 font-medium">根概念</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.root_concepts || 0}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-brand-gradient rounded-2xl shadow-brand p-6 border border-brand">
        <h2 className="text-lg font-semibold mb-4 text-brand-600">快速操作</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/papers"
            className="flex items-center p-4 bg-brand-fill rounded-xl hover:shadow-brand transition-all"
          >
            <div className="h-10 w-10 bg-brand-button rounded-lg flex items-center justify-center mr-3">
              <FileText className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-medium text-brand-700">上传论文</p>
              <p className="text-sm text-brand-500">上传 PDF 并提取概念</p>
            </div>
          </Link>

          <Link
            to="/concepts"
            className="flex items-center p-4 bg-brand-fill rounded-xl hover:shadow-brand transition-all"
          >
            <div className="h-10 w-10 bg-brand-button rounded-lg flex items-center justify-center mr-3">
              <GitBranch className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-medium text-brand-700">浏览概念</p>
              <p className="text-sm text-brand-500">查看概念层级树</p>
            </div>
          </Link>

          <button
            onClick={() => setShowLLMModal(true)}
            className="flex items-center p-4 bg-brand-fill rounded-xl hover:shadow-brand transition-all text-left"
          >
            <div className="h-10 w-10 bg-brand-button rounded-lg flex items-center justify-center mr-3">
              <Settings className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-medium text-brand-700">LLM 配置</p>
              <p className="text-sm text-brand-500">{llmStatus || '配置 AI 服务商'}</p>
            </div>
          </button>

          <button
            onClick={() => setShowS2Modal(true)}
            className="flex items-center p-4 bg-brand-fill rounded-xl hover:shadow-brand transition-all text-left"
          >
            <div className="h-10 w-10 bg-brand-button rounded-lg flex items-center justify-center mr-3">
              <Database className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-medium text-brand-700">S2 配置</p>
              <p className="text-sm text-brand-500">{s2Status || '配置元数据增强'}</p>
            </div>
          </button>
        </div>
      </div>

      {/* LLM Config Modal */}
      {showLLMModal && (
        <LLMConfigModal onClose={() => setShowLLMModal(false)} onSave={() => {
          setShowLLMModal(false)
          // Reload status
          llmApi.getConfig().then(res => {
            const config = res.data
            if (config.providers && config.providers.length > 0) {
              const p = config.providers[0]
              setLlmStatus(`${p.provider} (${p.model || 'default'})`)
            }
          })
        }} />
      )}

      {/* S2 Config Modal */}
      {showS2Modal && (
        <S2ConfigModal
          onClose={() => setShowS2Modal(false)}
          onSave={() => {
            setShowS2Modal(false)
            s2Api.getConfig().then(res => {
              if (res.data.has_api_key) {
                setS2Status(res.data.enabled ? '已启用' : '已禁用')
              } else {
                setS2Status('未配置')
              }
            })
          }}
        />
      )}

      {/* Onboarding Modal */}
      {showOnboarding && (
        <OnboardingModal
          onClose={() => setShowOnboarding(false)}
          onOpenLLMConfig={() => setShowLLMModal(true)}
        />
      )}

      {/* Paper Status */}
      {stats?.papers && (
        <div className="bg-brand-gradient rounded-2xl shadow-brand p-6 border border-brand">
          <h2 className="text-lg font-semibold mb-4 text-brand-600">论文状态</h2>
          <div className="flex gap-6">
            {Object.entries(stats.papers).filter(([k]) => k !== 'total').map(([status, count]) => (
              <div key={status} className="text-center p-4 bg-brand-fill rounded-xl">
                <p className="text-2xl font-bold text-brand-700">{count}</p>
                <p className="text-sm text-brand-500">{status}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}