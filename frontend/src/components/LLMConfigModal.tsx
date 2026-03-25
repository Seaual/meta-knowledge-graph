import { useEffect, useState } from 'react'
import { X, Check, Loader2 } from 'lucide-react'
import { llmApi } from '../lib/api'

interface Props {
  onClose: () => void
  onSave: () => void
}

interface ProviderConfig {
  function_group?: string
  provider: string
  api_key?: string
  base_url?: string
  model?: string
  is_active: boolean
}

export default function LLMConfigModal({ onClose, onSave }: Props) {
  const [mode, setMode] = useState<'single' | 'per_function'>('single')
  const [providers, setProviders] = useState<any[]>([])
  const [_functionGroups, setFunctionGroups] = useState<any[]>([])
  const [configs, setConfigs] = useState<ProviderConfig[]>([{ provider: 'openai', is_active: true }])
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    llmApi.providers().then(res => {
      setProviders(res.data.providers)
      setFunctionGroups(res.data.function_groups)
    })
    llmApi.getConfig().then(res => {
      if (res.data.mode) setMode(res.data.mode as 'single' | 'per_function')
      if (res.data.providers?.length > 0) setConfigs(res.data.providers)
    })
  }, [])

  const currentProvider = providers.find(p => p.value === configs[0]?.provider)
  const requiresApiKey = currentProvider?.requires_api_key ?? true

  const updateConfig = (index: number, field: string, value: any) => {
    setConfigs(prev => {
      const updated = [...prev]
      updated[index] = { ...updated[index], [field]: value }
      return updated
    })
    setTestResult(null)
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const config = configs[0]
      const res = await llmApi.test({
        provider: config.provider,
        api_key: config.api_key,
        base_url: config.base_url,
        model: config.model,
      })
      setTestResult({ success: true, message: res.data.message })
    } catch (err: any) {
      setTestResult({ success: false, message: err.response?.data?.detail || '测试失败' })
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await llmApi.saveConfig({ mode, providers: configs })
      onSave()
    } catch (err) {
      alert('保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">LLM 服务配置</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Mode */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">配置模式</label>
            <div className="flex gap-2">
              <button
                onClick={() => setMode('single')}
                className={`flex-1 py-2 px-4 rounded-lg border text-sm font-medium ${
                  mode === 'single' ? 'border-purple-500 bg-purple-50 text-purple-700' : 'border-gray-200 text-gray-600'
                }`}
              >
                单一服务商
              </button>
              <button
                onClick={() => setMode('per_function')}
                className={`flex-1 py-2 px-4 rounded-lg border text-sm font-medium ${
                  mode === 'per_function' ? 'border-purple-500 bg-purple-50 text-purple-700' : 'border-gray-200 text-gray-600'
                }`}
              >
                按功能分配
              </button>
            </div>
          </div>

          {/* Provider Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">服务商</label>
            <select
              value={configs[0]?.provider || 'openai'}
              onChange={e => updateConfig(0, 'provider', e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm"
            >
              {providers.map(p => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>

          {/* Claude CLI notice */}
          {configs[0]?.provider === 'claude_cli' && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700">
              <Check className="inline h-4 w-4 mr-1" />
              Claude Code CLI 仅限本地开发使用，Docker 环境不可用
            </div>
          )}

          {/* API Key */}
          {requiresApiKey && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">API Key</label>
              <input
                type="password"
                value={configs[0]?.api_key || ''}
                onChange={e => updateConfig(0, 'api_key', e.target.value)}
                placeholder="sk-..."
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          )}

          {/* Base URL */}
          {requiresApiKey && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Base URL（可选）</label>
              <input
                type="text"
                value={configs[0]?.base_url || ''}
                onChange={e => updateConfig(0, 'base_url', e.target.value)}
                placeholder={currentProvider?.default_base_url || 'https://api.openai.com/v1'}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          )}

          {/* Model */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">模型</label>
            <input
              type="text"
              value={configs[0]?.model || ''}
              onChange={e => updateConfig(0, 'model', e.target.value)}
              placeholder="gpt-4, claude-sonnet-4-20250514, gemini-2.0-flash..."
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
          </div>

          {/* Test Result */}
          {testResult && (
            <div className={`rounded-lg p-3 text-sm ${testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
              {testResult.message}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-2 p-4 border-t bg-gray-50">
          <button
            onClick={handleTest}
            disabled={testing}
            className="flex-1 py-2 px-4 rounded-lg border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-50"
          >
            {testing ? <Loader2 className="inline h-4 w-4 animate-spin mr-1" /> : null}
            测试连接
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 py-2 px-4 rounded-lg bg-purple-600 text-white text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
          >
            {saving ? '保存中...' : '保存配置'}
          </button>
        </div>
      </div>
    </div>
  )
}