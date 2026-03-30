import { useState } from 'react'
import { X, FolderPlus } from 'lucide-react'
import { useTranslation } from '../i18n'

interface Props {
  onClose: () => void
  onCreate: (name: string, description: string) => void
}

export default function CreateFolderModal({ onClose, onCreate }: Props) {
  const { t } = useTranslation()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    onCreate(name.trim(), description.trim())
  }

  return (
    <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50 p-4">
      <div className="modal-academic w-full max-w-md animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-academic">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-medium bg-gradient-amber flex items-center justify-center">
              <FolderPlus className="w-5 h-5 text-vellum" />
            </div>
            <h2 className="font-display text-lg text-sepia font-medium">{t.modal.createFolder.title}</h2>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-soft text-muted hover:text-sepia hover:bg-paper flex items-center justify-center transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-5">
          <div>
            <label className="font-mono text-xs text-muted uppercase tracking-wider mb-2 block">
              {t.modal.createFolder.name} <span className="text-status-error">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder={t.modal.createFolder.namePlaceholder}
              className="input-academic w-full"
              autoFocus
            />
          </div>

          <div>
            <label className="font-mono text-xs text-muted uppercase tracking-wider mb-2 block">
              {t.modal.createFolder.description}
            </label>
            <input
              type="text"
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder={t.modal.createFolder.descPlaceholder}
              className="input-academic w-full"
            />
          </div>
        </form>

        {/* Footer */}
        <div className="flex gap-3 p-5 border-t border-academic bg-paper/50">
          <button
            type="button"
            onClick={onClose}
            className="btn-secondary flex-1"
          >
            {t.modal.cancel}
          </button>
          <button
            onClick={handleSubmit}
            disabled={!name.trim()}
            className="btn-primary flex-1"
          >
            {t.modal.createFolder.create}
          </button>
        </div>
      </div>
    </div>
  )
}