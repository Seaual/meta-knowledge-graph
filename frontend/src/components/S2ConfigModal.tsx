import { useEffect, useState } from 'react'
import { X, Check, Loader2, Database } from 'lucide-react'
import { s2Api } from '../lib/api'

interface Props {
  onClose: () => void
  onSave: () => void
}

export default function S2ConfigModal({ onClose, onSave }: Props) {
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
      const errorMsg = err.response?.data?.detail || '测试失败'
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
      alert('保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5 text-purple-600" />
            <h2 className="text-lg font-semibold">Semantic Scholar 配置</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Status */}
          {hasKey && maskedKey && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700">
              <Check className="inline h-4 w-4 mr-1" />
              已配置 API Key: {maskedKey}
            </div>
          )}

          {/* API Key */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              API Key {!hasKey && <span className="text-red-500">*</span>}
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={e => {
                setApiKey(e.target.value)
                setTestResult(null)
              }}
              placeholder={hasKey ? "输入新 Key 更换" : "输入 Semantic Scholar API Key"}
              className="w-full border rounded-lg px-3 py-2 text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">
              申请地址: <a href="https://www.semanticscholar.org/product/api" target="_blank" className="text-purple-600 hover:underline">Semantic Scholar API</a>
            </p>
          </div>

          {/* Enable Switch */}
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700">
              启用自动增强
            </label>
            <button
              onClick={() => setEnabled(!enabled)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                enabled ? 'bg-purple-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Test Result */}
          {testResult && (
            <div className={`rounded-lg p-3 text-sm ${
              testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
            }`}>
              {testResult.message}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-2 p-4 border-t bg-gray-50">
          <button
            onClick={handleTest}
            disabled={testing || !apiKey}
            className="flex-1 py-2 px-4 rounded-lg border border-gray-200 text-sm font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-50"
          >
            {testing ? <Loader2 className="inline h-4 w-4 animate-spin mr-1" /> : null}
            测试连接
          </button>
          <button
            onClick={handleSave}
            disabled={saving || (!apiKey && !hasKey)}
            className="flex-1 py-2 px-4 rounded-lg bg-purple-600 text-white text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
          >
            {saving ? '保存中...' : '保存配置'}
          </button>
        </div>
      </div>
    </div>
  )
}