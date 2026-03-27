import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText, GitBranch, Network, TrendingUp, Settings } from 'lucide-react'
import { graphApi, llmApi } from '../lib/api'
import LLMConfigModal from '../components/LLMConfigModal'

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

  if (loading) {
    return <div className="text-center py-12">加载中...</div>
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Meta Knowledge Graph</h1>
        <p className="mt-2 text-gray-600">学术知识图谱引擎</p>
      </div>

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
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">快速操作</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/papers"
            className="flex items-center p-4 border rounded-lg hover:bg-gray-50"
          >
            <FileText className="h-6 w-6 text-blue-500 mr-3" />
            <div>
              <p className="font-medium">上传论文</p>
              <p className="text-sm text-gray-500">上传 PDF 并提取概念</p>
            </div>
          </Link>

          <Link
            to="/concepts"
            className="flex items-center p-4 border rounded-lg hover:bg-gray-50"
          >
            <GitBranch className="h-6 w-6 text-green-500 mr-3" />
            <div>
              <p className="font-medium">浏览概念</p>
              <p className="text-sm text-gray-500">查看概念层级树</p>
            </div>
          </Link>

          <button
            onClick={() => setShowLLMModal(true)}
            className="flex items-center p-4 border rounded-lg hover:bg-purple-50 text-left"
          >
            <Settings className="h-6 w-6 text-purple-500 mr-3" />
            <div>
              <p className="font-medium">LLM 配置</p>
              <p className="text-sm text-gray-500">{llmStatus || '配置 AI 服务商'}</p>
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

      {/* Paper Status */}
      {stats?.papers && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">论文状态</h2>
          <div className="flex gap-6">
            {Object.entries(stats.papers).filter(([k]) => k !== 'total').map(([status, count]) => (
              <div key={status} className="text-center">
                <p className="text-2xl font-bold">{count}</p>
                <p className="text-sm text-gray-500">{status}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}