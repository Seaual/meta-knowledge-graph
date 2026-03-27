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
  custom_model?: string
  is_active: boolean
}

export default function LLMConfigModal({ onClose, onSave }: Props) {
  const [configType, setConfigType] = useState<'claude_cli' | 'custom'>('custom')
  const [configs, setConfigs] = useState<ProviderConfig[]>([{ provider: 'custom', is_active: true }])
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    llmApi.getConfig().then(res => {
      if (res.data.providers?.length > 0) {
        const savedConfig = res.data.providers[0]
        setConfigs(res.data.providers)
        // Set configType based on saved provider
        if (savedConfig.provider === 'claude_cli') {
          setConfigType('claude_cli')
        } else {
          setConfigType('custom')
        }
      }
    })
  }, [])

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
      const errorMsg = err.response?.data?.detail || '测试失败'
      setTestResult({ success: false, message: errorMsg })
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const config = configs[0]
      await llmApi.saveConfig({ mode: 'single', providers: [config] })
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
          {/* Config Type Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">配置类型</label>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setConfigType('claude_cli')
                  setConfigs([{ provider: 'claude_cli', is_active: true }])
                  setTestResult(null)
                }}
                className={`flex-1 py-2 px-4 rounded-lg border text-sm font-medium ${
                  configType === 'claude_cli' ? 'border-purple-500 bg-purple-50 text-purple-700' : 'border-gray-200 text-gray-600'
                }`}
              >
                Claude Code CLI
              </button>
              <button
                onClick={() => {
                  setConfigType('custom')
                  setConfigs([{ provider: 'custom', is_active: true }])
                  setTestResult(null)
                }}
                className={`flex-1 py-2 px-4 rounded-lg border text-sm font-medium ${
                  configType === 'custom' ? 'border-purple-500 bg-purple-50 text-purple-700' : 'border-gray-200 text-gray-600'
                }`}
              >
                自定义配置
              </button>
            </div>
          </div>

          {/* Claude CLI notice */}
          {configType === 'claude_cli' && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700">
              <Check className="inline h-4 w-4 mr-1" />
              Claude Code CLI 仅限本地开发使用，Docker 环境不可用
            </div>
          )}

          {/* Custom Config Form */}
          {configType === 'custom' && (
            <>
              {/* Base URL */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Base URL <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={configs[0]?.base_url || ''}
                  onChange={e => updateConfig(0, 'base_url', e.target.value)}
                  placeholder="https://api.openai.com/v1"
                  className={`w-full border rounded-lg px-3 py-2 text-sm ${!configs[0]?.base_url ? 'border-red-300' : ''}`}
                />
                <p className="text-xs text-gray-500 mt-1">支持 OpenAI/Anthropic 官方 API 及兼容服务</p>
              </div>

              {/* API Key */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  API Key <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  value={configs[0]?.api_key || ''}
                  onChange={e => updateConfig(0, 'api_key', e.target.value)}
                  placeholder="sk-..."
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>

              {/* Model Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  模型名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={configs[0]?.model || ''}
                  onChange={e => updateConfig(0, 'model', e.target.value)}
                  placeholder="gpt-4o-mini, claude-3-5-sonnet-20241022..."
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
            </>
          )}

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