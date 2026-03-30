import { useEffect, useState } from 'react'
import { X, Check, Loader2, Database } from 'lucide-react'
import { s2Api } from '../lib/api'
import { useTranslation } from '../i18n'

interface Props {
  onClose: () => void
  onSave: () => void
}

export default function S2ConfigModal({ onClose, onSave }: Props) {
  const { t } = useTranslation()
  const [apiKey, setApiKey] = useState('')
  const [enabled, setEnabled] = useState(true)
  const [hasKey, setHasKey] = useState(false)
  const [maskedKey, setMaskedKey] = useState<string | null>(null)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    s2Api.getConfig().then(res => {
      setHasKey(res.data.has_api_key)
      setEnabled(res.data.enabled)
      setMaskedKey(res.data.masked_key || null)
    }).catch(() => {
      setHasKey(false)
    })
  }, [])

  const handleTest = async () => {
    if (!apiKey) return
    setTesting(true)
    setTestResult(null)
    try {
      const res = await s2Api.test(apiKey)
      setTestResult({ success: res.data.success, message: res.data.message })
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Test failed'
      setTestResult({ success: false, message: errorMsg })
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    if (!apiKey && !hasKey) return
    setSaving(true)
    try {
      await s2Api.saveConfig({ api_key: apiKey, enabled })
      onSave()
    } catch (err) {
      alert('Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50 p-4">
      <div className="modal-academic w-full max-w-md animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-academic">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-medium bg-gradient-amber flex items-center justify-center">
              <Database className="w-5 h-5 text-vellum" />
            </div>
            <h2 className="font-display text-lg text-sepia font-medium">{t.modal.s2Config.title}</h2>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-soft text-muted hover:text-sepia hover:bg-paper flex items-center justify-center transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-5">
          {/* Status */}
          {hasKey && maskedKey && (
            <div className="bg-status-success/5 border border-status-success/20 rounded-medium p-3 font-body text-sm text-status-success">
              <Check className="inline h-4 h-4 mr-1" />
              {t.modal.s2Config.configured}: {maskedKey}
            </div>
          )}

          {/* API Key */}
          <div>
            <label className="font-mono text-xs text-muted uppercase tracking-wider mb-2 block">
              {t.modal.s2Config.apiKey} {!hasKey && <span className="text-status-error">*</span>}
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={e => {
                setApiKey(e.target.value)
                setTestResult(null)
              }}
              placeholder={hasKey ? t.modal.s2Config.enterNew : t.modal.s2Config.apiKeyPlaceholder}
              className="input-academic w-full"
            />
            <p className="font-body text-xs text-faint mt-1">
              {t.modal.s2Config.apiKeyHint}: <a href="https://www.semanticscholar.org/product/api" target="_blank" className="text-status-info hover:text-sepia hover:underline">Semantic Scholar API</a>
            </p>
          </div>

          {/* Enable Switch */}
          <div className="flex items-center justify-between py-2">
            <label className="font-body text-sm text-sepia">
              {t.modal.s2Config.enableAuto}
            </label>
            <button
              onClick={() => setEnabled(!enabled)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                enabled ? 'bg-sepia' : 'bg-paper'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-vellum shadow-paper transition-transform ${
                  enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

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
            disabled={testing || !apiKey}
            className="btn-secondary flex-1 flex items-center justify-center gap-2"
          >
            {testing && <Loader2 className="w-4 h-4 animate-spin" />}
            {t.modal.test}
          </button>
          <button
            onClick={handleSave}
            disabled={saving || (!apiKey && !hasKey)}
            className="btn-primary flex-1"
          >
            {saving ? t.modal.llmConfig.saving : t.modal.save}
          </button>
        </div>
      </div>
    </div>
  )
}