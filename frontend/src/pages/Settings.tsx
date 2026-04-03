// Settings.tsx - Settings Page
import { useState, useEffect } from 'react'
import { useTranslation } from '../i18n'
import { foldersApi } from '../lib/api'
import { Database, Key, Globe, Folder, Save, Check } from 'lucide-react'

interface LLMConfig {
  mode: string
  providers: {
    id?: number
    provider: string
    api_key: string
    base_url: string
    model: string
    is_active: boolean
  }[]
}

export default function Settings() {
  const { language, toggleLanguage } = useTranslation()
  const [llmConfig, setLlmConfig] = useState<LLMConfig | null>(null)
  const [folders, setFolders] = useState<{ id: string; name: string }[]>([])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  // Load config
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await fetch('/api/llm/config')
        if (res.ok) {
          const data = await res.json()
          setLlmConfig(data)
        }
      } catch (e) {
        console.error('Failed to load LLM config:', e)
      }
    }

    const loadFolders = async () => {
      try {
        const res = await foldersApi.list()
        setFolders(res.data || [])
      } catch (e) {
        console.error('Failed to load folders:', e)
      }
    }

    loadConfig()
    loadFolders()
  }, [])

  // Save LLM config
  const handleSaveConfig = async () => {
    if (!llmConfig) return

    setSaving(true)
    try {
      const res = await fetch('/api/llm/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(llmConfig),
      })

      if (res.ok) {
        setSaved(true)
        setTimeout(() => setSaved(false), 2000)
      }
    } catch (e) {
      console.error('Failed to save:', e)
    } finally {
      setSaving(false)
    }
  }

  // Update provider field
  const updateProvider = (index: number, field: string, value: string | boolean) => {
    if (!llmConfig) return

    const newProviders = [...llmConfig.providers]
    newProviders[index] = { ...newProviders[index], [field]: value }

    // If setting active, deactivate others
    if (field === 'is_active' && value === true) {
      newProviders.forEach((p, i) => {
        if (i !== index) p.is_active = false
      })
    }

    setLlmConfig({ ...llmConfig, providers: newProviders })
  }

  return (
    <div className="h-full overflow-y-auto" style={{ background: 'var(--color-cream)' }}>
      <div className="max-w-3xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-display text-2xl font-medium" style={{ color: 'var(--color-sepia)' }}>
            设置
          </h1>
          <p className="font-body text-sm mt-1" style={{ color: 'var(--color-muted)' }}>
            配置 API、语言和存储选项
          </p>
        </div>

        {/* LLM Configuration */}
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Key className="w-5 h-5" style={{ color: 'var(--color-amber)' }} />
            <h2 className="font-display text-lg font-medium" style={{ color: 'var(--color-sepia)' }}>
              LLM 配置
            </h2>
          </div>

          {llmConfig?.providers?.map((provider, index) => (
            <div
              key={index}
              className="p-5 rounded-xl mb-4"
              style={{
                background: 'var(--color-vellum)',
                border: '1px solid rgba(184, 134, 11, 0.1)',
              }}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <select
                    value={provider.provider}
                    onChange={(e) => updateProvider(index, 'provider', e.target.value)}
                    className="px-3 py-2 rounded-lg font-body text-sm"
                    style={{
                      background: 'var(--color-paper)',
                      border: '1px solid rgba(184, 134, 11, 0.12)',
                      color: 'var(--color-ink)',
                    }}
                  >
                    <option value="openai">OpenAI</option>
                    <option value="deepseek">DeepSeek</option>
                    <option value="custom">Custom</option>
                  </select>

                  {provider.is_active && (
                    <span
                      className="px-2 py-0.5 rounded text-xs font-mono"
                      style={{
                        background: 'rgba(45, 90, 39, 0.1)',
                        color: '#2d5a27',
                      }}
                    >
                      当前使用
                    </span>
                  )}
                </div>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={provider.is_active}
                    onChange={(e) => updateProvider(index, 'is_active', e.target.checked)}
                    className="w-4 h-4 rounded"
                  />
                  <span className="font-body text-sm" style={{ color: 'var(--color-muted)' }}>
                    启用
                  </span>
                </label>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-mono text-xs uppercase tracking-wider mb-1.5" style={{ color: 'var(--color-faint)' }}>
                    Model
                  </label>
                  <input
                    type="text"
                    value={provider.model}
                    onChange={(e) => updateProvider(index, 'model', e.target.value)}
                    placeholder="gpt-4o / deepseek-chat"
                    className="w-full px-3 py-2 rounded-lg font-mono text-sm"
                    style={{
                      background: 'var(--color-paper)',
                      border: '1px solid rgba(184, 134, 11, 0.12)',
                      color: 'var(--color-ink)',
                    }}
                  />
                </div>

                <div>
                  <label className="block font-mono text-xs uppercase tracking-wider mb-1.5" style={{ color: 'var(--color-faint)' }}>
                    API Key
                  </label>
                  <input
                    type="password"
                    value={provider.api_key}
                    onChange={(e) => updateProvider(index, 'api_key', e.target.value)}
                    placeholder="sk-..."
                    className="w-full px-3 py-2 rounded-lg font-mono text-sm"
                    style={{
                      background: 'var(--color-paper)',
                      border: '1px solid rgba(184, 134, 11, 0.12)',
                      color: 'var(--color-ink)',
                    }}
                  />
                </div>

                <div className="col-span-2">
                  <label className="block font-mono text-xs uppercase tracking-wider mb-1.5" style={{ color: 'var(--color-faint)' }}>
                    Base URL (可选)
                  </label>
                  <input
                    type="text"
                    value={provider.base_url}
                    onChange={(e) => updateProvider(index, 'base_url', e.target.value)}
                    placeholder="https://api.openai.com/v1"
                    className="w-full px-3 py-2 rounded-lg font-mono text-sm"
                    style={{
                      background: 'var(--color-paper)',
                      border: '1px solid rgba(184, 134, 11, 0.12)',
                      color: 'var(--color-ink)',
                    }}
                  />
                </div>
              </div>
            </div>
          ))}

          <button
            onClick={handleSaveConfig}
            disabled={saving}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-body text-sm font-medium transition-all"
            style={{
              background: 'linear-gradient(135deg, var(--color-sepia) 0%, var(--color-copper) 100%)',
              color: 'var(--color-vellum)',
            }}
          >
            {saving ? (
              <>保存中...</>
            ) : saved ? (
              <>
                <Check className="w-4 h-4" />
                已保存
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                保存配置
              </>
            )}
          </button>
        </section>

        {/* Language */}
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Globe className="w-5 h-5" style={{ color: 'var(--color-amber)' }} />
            <h2 className="font-display text-lg font-medium" style={{ color: 'var(--color-sepia)' }}>
              语言 / Language
            </h2>
          </div>

          <div
            className="p-5 rounded-xl"
            style={{
              background: 'var(--color-vellum)',
              border: '1px solid rgba(184, 134, 11, 0.1)',
            }}
          >
            <div className="flex items-center justify-between">
              <span className="font-body text-sm" style={{ color: 'var(--color-ink)' }}>
                当前语言 / Current: {language === 'zh' ? '中文' : 'English'}
              </span>
              <button
                onClick={toggleLanguage}
                className="px-4 py-2 rounded-lg font-body text-sm transition-colors"
                style={{
                  background: 'var(--color-paper)',
                  border: '1px solid rgba(184, 134, 11, 0.12)',
                  color: 'var(--color-sepia)',
                }}
              >
                切换 / Switch
              </button>
            </div>
          </div>
        </section>

        {/* Folders */}
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Folder className="w-5 h-5" style={{ color: 'var(--color-amber)' }} />
            <h2 className="font-display text-lg font-medium" style={{ color: 'var(--color-sepia)' }}>
              文件夹
            </h2>
          </div>

          <div
            className="p-5 rounded-xl"
            style={{
              background: 'var(--color-vellum)',
              border: '1px solid rgba(184, 134, 11, 0.1)',
            }}
          >
            {folders.length > 0 ? (
              <div className="space-y-2">
                {folders.map((folder) => (
                  <div
                    key={folder.id}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg"
                    style={{ background: 'var(--color-paper)' }}
                  >
                    <Folder className="w-4 h-4" style={{ color: 'var(--color-amber)' }} />
                    <span className="font-body text-sm" style={{ color: 'var(--color-ink)' }}>
                      {folder.name}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="font-body text-sm" style={{ color: 'var(--color-muted)' }}>
                暂无文件夹
              </p>
            )}
          </div>
        </section>

        {/* Database Info */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Database className="w-5 h-5" style={{ color: 'var(--color-amber)' }} />
            <h2 className="font-display text-lg font-medium" style={{ color: 'var(--color-sepia)' }}>
              数据库
            </h2>
          </div>

          <div
            className="p-5 rounded-xl"
            style={{
              background: 'var(--color-vellum)',
              border: '1px solid rgba(184, 134, 11, 0.1)',
            }}
          >
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="font-display text-2xl" style={{ color: 'var(--color-sepia)' }}>
                  2
                </div>
                <div className="font-mono text-xs" style={{ color: 'var(--color-muted)' }}>
                  论文
                </div>
              </div>
              <div>
                <div className="font-display text-2xl" style={{ color: 'var(--color-sepia)' }}>
                  15
                </div>
                <div className="font-mono text-xs" style={{ color: 'var(--color-muted)' }}>
                  概念
                </div>
              </div>
              <div>
                <div className="font-display text-2xl" style={{ color: 'var(--color-sepia)' }}>
                  3
                </div>
                <div className="font-mono text-xs" style={{ color: 'var(--color-muted)' }}>
                  对话
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}