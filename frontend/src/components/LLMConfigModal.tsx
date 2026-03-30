import { useEffect, useState } from 'react'
import { X, Check, Loader2 } from 'lucide-react'
import { llmApi } from '../lib/api'
import { useTranslation } from '../i18n'

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
  const { t } = useTranslation()
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
      const errorMsg = err.response?.data?.detail || 'Test failed'
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
      alert('Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50 p-4">
      <div className="modal-academic w-full max-w-lg max-h-[90vh] overflow-y-auto animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-academic">
          <h2 className="font-display text-lg text-sepia font-medium">{t.modal.llmConfig.title}</h2>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-soft text-muted hover:text-sepia hover:bg-paper flex items-center justify-center transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-5">
          {/* Config Type Selection */}
          <div>
            <label className="font-mono text-xs text-muted uppercase tracking-wider mb-2 block">{t.modal.llmConfig.configType}</label>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setConfigType('claude_cli')
                  setConfigs([{ provider: 'claude_cli', is_active: true }])
                  setTestResult(null)
                }}
                className={`flex-1 py-2.5 px-4 rounded-medium font-body text-sm transition-all ${
                  configType === 'claude_cli'
                    ? 'bg-vellum border-2 border-sepia text-sepia'
                    : 'bg-paper border border-academic text-muted hover:text-sepia'
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
                className={`flex-1 py-2.5 px-4 rounded-medium font-body text-sm transition-all ${
                  configType === 'custom'
                    ? 'bg-vellum border-2 border-sepia text-sepia'
                    : 'bg-paper border border-academic text-muted hover:text-sepia'
                }`}
              >
                {t.modal.llmConfig.customConfig}
              </button>
            </div>
          </div>

          {/* Claude CLI notice */}
          {configType === 'claude_cli' && (
            <div className="bg-status-success/5 border border-status-success/20 rounded-medium p-3 font-body text-sm text-status-success">
              <Check className="inline h-4 w-4 mr-1" />
              {t.modal.llmConfig.cliNotice}
            </div>
          )}

          {/* Custom Config Form */}
          {configType === 'custom' && (
            <>
              {/* Base URL */}
              <div>
                <label className="font-mono text-xs text-muted uppercase tracking-wider mb-2 block">
                  {t.modal.llmConfig.baseUrl} <span className="text-status-error">*</span>
                </label>
                <input
                  type="text"
                  value={configs[0]?.base_url || ''}
                  onChange={e => updateConfig(0, 'base_url', e.target.value)}
                  placeholder={t.modal.llmConfig.baseUrlPlaceholder}
                  className={`input-academic w-full ${!configs[0]?.base_url ? 'border-status-error' : ''}`}
                />
                <p className="font-body text-xs text-faint mt-1">{t.modal.llmConfig.baseUrlHint}</p>
              </div>

              {/* API Key */}
              <div>
                <label className="font-mono text-xs text-muted uppercase tracking-wider mb-2 block">
                  {t.modal.llmConfig.apiKey} <span className="text-status-error">*</span>
                </label>
                <input
                  type="password"
                  value={configs[0]?.api_key || ''}
                  onChange={e => updateConfig(0, 'api_key', e.target.value)}
                  placeholder={t.modal.llmConfig.apiKeyPlaceholder}
                  className="input-academic w-full"
                />
              </div>

              {/* Model Name */}
              <div>
                <label className="font-mono text-xs text-muted uppercase tracking-wider mb-2 block">
                  {t.modal.llmConfig.modelName} <span className="text-status-error">*</span>
                </label>
                <input
                  type="text"
                  value={configs[0]?.model || ''}
                  onChange={e => updateConfig(0, 'model', e.target.value)}
                  placeholder={t.modal.llmConfig.modelNamePlaceholder}
                  className="input-academic w-full"
                />
              </div>
            </>
          )}

          {/* Test Result */}
          {testResult && (
            <div
              className={`rounded-medium p-3 font-body text-sm ${
                testResult.success
                  ? 'bg-status-success/5 border border-status-success/20 text-status-success'
                  : 'bg-status-error/5 border border-status-error/20 text-status-error'
              }`}
            >
              {testResult.message}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 p-5 border-t border-academic bg-paper/50">
          <button
            onClick={handleTest}
            disabled={testing}
            className="btn-secondary flex-1 flex items-center justify-center gap-2"
          >
            {testing && <Loader2 className="w-4 h-4 animate-spin" />}
            {t.modal.llmConfig.testConnection}
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary flex-1"
          >
            {saving ? t.modal.llmConfig.saving : t.modal.llmConfig.saveConfig}
          </button>
        </div>
      </div>
    </div>
  )
}