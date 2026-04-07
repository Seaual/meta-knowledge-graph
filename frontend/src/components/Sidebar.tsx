// Sidebar.tsx - Minimal Navigation for Meta Knowledge Graph
import { useState, useCallback, useEffect } from 'react'
import { NavLink, useLocation, Link } from 'react-router-dom'
import { useTranslation } from '../i18n'
import ConversationHistory from './ConversationHistory'
import { useConversationStore } from '../stores/conversationStore'
import {
  Home,
  MessageSquare,
  Network,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Plus,
  Globe,
} from 'lucide-react'

interface NavItem {
  path: string
  icon: React.ReactNode
  labelKey: string
}

const navItems: NavItem[] = [
  { path: '/', icon: <Home className="w-[18px] h-[18px]" />, labelKey: 'home' },
  { path: '/chat', icon: <MessageSquare className="w-[18px] h-[18px]" />, labelKey: 'chat' },
  { path: '/concepts', icon: <Network className="w-[18px] h-[18px]" />, labelKey: 'concepts' },
  { path: '/papers', icon: <FileText className="w-[18px] h-[18px]" />, labelKey: 'papers' },
  { path: '/settings', icon: <Settings className="w-[18px] h-[18px]" />, labelKey: 'settings' },
]

export default function Sidebar() {
  const { t, language, toggleLanguage } = useTranslation()
  const location = useLocation()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const { loadConversations, createConversation } = useConversationStore()

  // Load conversations on mount
  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  const toggleSidebar = useCallback(() => {
    setIsCollapsed(prev => !prev)
  }, [])

  const sidebarWidth = isCollapsed ? 64 : 220

  return (
    <aside
      className="flex flex-col h-full"
      style={{
        width: sidebarWidth,
        background: 'var(--color-surface)',
        borderRight: '1px solid var(--color-border-subtle)',
        transition: 'width 250ms cubic-bezier(0.25, 1, 0.5, 1)',
      }}
    >
      {/* Logo */}
      <div
        className="flex items-center gap-3 px-4 py-5"
      >
        <Link to="/" className="flex items-center gap-3 group">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center"
            style={{
              background: 'var(--color-accent)',
            }}
          >
            <span className="font-display text-white text-base font-semibold">M</span>
          </div>
          {!isCollapsed && (
            <div className="overflow-hidden">
              <div
                className="font-display text-base font-medium whitespace-nowrap"
                style={{ color: 'var(--color-ink)' }}
              >
                MKG
              </div>
              <div
                className="font-mono text-[10px] whitespace-nowrap"
                style={{ color: 'var(--color-ink-muted)' }}
              >
                Knowledge Graph
              </div>
            </div>
          )}
        </Link>
      </div>

      {/* New Chat Button */}
      {!isCollapsed && (
        <div className="px-3 pb-3">
          <button
            onClick={async () => {
              await createConversation()
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-body text-sm font-medium transition-all"
            style={{
              background: 'var(--color-accent)',
              color: 'white',
            }}
          >
            <Plus className="w-4 h-4" />
            <span>新对话</span>
          </button>
        </div>
      )}

      {/* Conversation History */}
      {!isCollapsed && (
        <ConversationHistory onSelect={() => {
          // Could close mobile sidebar here if needed
        }} />
      )}

      {/* Navigation */}
      <nav className="flex-1 px-2 py-2">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path
          const label = item.labelKey === 'home' ? t.nav.home :
                       item.labelKey === 'chat' ? 'AI 对话' :
                       item.labelKey === 'concepts' ? t.nav.concepts :
                       item.labelKey === 'papers' ? t.nav.papers :
                       item.labelKey === 'settings' ? '设置' : item.labelKey

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150"
              style={{
                color: isActive ? 'var(--color-accent)' : 'var(--color-ink-tertiary)',
                backgroundColor: isActive ? 'var(--color-highlight-soft)' : 'transparent',
                fontWeight: isActive ? 500 : 400,
              }}
            >
              <span className="flex-shrink-0">{item.icon}</span>
              {!isCollapsed && (
                <span className="font-body text-sm whitespace-nowrap overflow-hidden">
                  {label}
                </span>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Bottom Section */}
      <div className="px-2 py-3 border-t" style={{ borderColor: 'var(--color-border-subtle)' }}>
        {/* Language Toggle */}
        <button
          onClick={toggleLanguage}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors duration-150"
          style={{ color: 'var(--color-ink-tertiary)' }}
          title={language === 'zh' ? 'Switch to English' : '切换到中文'}
        >
          <Globe className="w-[18px] h-[18px]" />
          {!isCollapsed && (
            <span className="font-body text-sm">
              {language === 'zh' ? 'English' : '中文'}
            </span>
          )}
        </button>

        {/* Collapse Toggle */}
        <button
          onClick={toggleSidebar}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors duration-150 mt-1"
          style={{ color: 'var(--color-ink-tertiary)' }}
        >
          {isCollapsed ? (
            <ChevronRight className="w-[18px] h-[18px]" />
          ) : (
            <>
              <ChevronLeft className="w-[18px] h-[18px]" />
              <span className="font-body text-sm">收起</span>
            </>
          )}
        </button>
      </div>
    </aside>
  )
}