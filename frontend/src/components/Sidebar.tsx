// Sidebar.tsx - Minimal Navigation for Meta Knowledge Graph
import { useState, useCallback, useEffect } from "react";
import { NavLink, useLocation, Link } from "react-router-dom";
import { useTranslation } from "../i18n";
import ConversationHistory from "./ConversationHistory";
import { useConversationStore } from "../stores/conversationStore";
import {
  Home,
  MessageSquare,
  Network,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Globe,
} from "lucide-react";

interface NavItem {
  path: string;
  icon: React.ReactNode;
  labelKey: string;
}

const navItems: NavItem[] = [
  { path: "/", icon: <Home className="w-[18px] h-[18px]" />, labelKey: "home" },
  {
    path: "/concepts",
    icon: <Network className="w-[18px] h-[18px]" />,
    labelKey: "concepts",
  },
  {
    path: "/papers",
    icon: <FileText className="w-[18px] h-[18px]" />,
    labelKey: "papers",
  },
  {
    path: "/settings",
    icon: <Settings className="w-[18px] h-[18px]" />,
    labelKey: "settings",
  },
];

export default function Sidebar() {
  const { t, language, toggleLanguage } = useTranslation();
  const location = useLocation();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { loadConversations, conversations } = useConversationStore();

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const toggleSidebar = useCallback(() => {
    setIsCollapsed((prev) => !prev);
  }, []);

  const sidebarWidth = isCollapsed ? 64 : 220;

  return (
    <aside
      className="flex flex-col h-full"
      style={{
        width: sidebarWidth,
        background: "var(--color-surface)",
        borderRight: "1px solid var(--color-border-subtle)",
        transition: "width 250ms cubic-bezier(0.25, 1, 0.5, 1)",
      }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5">
        <Link to="/" className="flex items-center gap-3 group">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center"
            style={{
              background: "var(--color-accent)",
            }}
          >
            <span className="font-display text-white text-base font-semibold">
              M
            </span>
          </div>
          {!isCollapsed && (
            <div className="overflow-hidden">
              <div
                className="font-display text-base font-medium whitespace-nowrap"
                style={{ color: "var(--color-ink)" }}
              >
                MKG
              </div>
              <div
                className="font-mono text-[10px] whitespace-nowrap"
                style={{ color: "var(--color-ink-muted)" }}
              >
                Knowledge Graph
              </div>
            </div>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-2">
        {/* 新对话按钮 - 在首页上方 */}
        {!isCollapsed && (
          <Link
            to="/chat"
            onClick={() =>
              useConversationStore.getState().clearCurrentConversation()
            }
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg transition-colors mb-2"
            style={{
              color: "var(--color-cream)",
              background:
                "linear-gradient(135deg, var(--color-accent) 0%, var(--color-copper) 100%)",
            }}
          >
            <MessageSquare className="w-[18px] h-[18px]" />
            <span className="font-body text-sm font-medium">{t.common.newChat}</span>
          </Link>
        )}

        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          const label =
            item.labelKey === "home"
              ? t.nav.home
              : item.labelKey === "concepts"
                ? t.nav.concepts
                : item.labelKey === "papers"
                  ? t.nav.papers
                  : item.labelKey === "settings"
                    ? t.nav.settings
                    : item.labelKey;

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150"
              style={{
                color: isActive
                  ? "var(--color-accent)"
                  : "var(--color-ink-tertiary)",
                backgroundColor: isActive
                  ? "var(--color-highlight-soft)"
                  : "transparent",
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
          );
        })}

        {/* Conversation History - Below settings, inside nav area */}
        {!isCollapsed && conversations.length > 0 && (
          <div
            className="mt-2 pt-2 border-t"
            style={{ borderColor: "var(--color-border-subtle)" }}
          >
            <div
              className="text-xs px-3 py-1"
              style={{ color: "var(--color-ink-muted)" }}
            >
              {t.common.conversationHistory}
            </div>
            <ConversationHistory onSelect={() => {}} />
          </div>
        )}
      </nav>

      {/* Bottom Section */}
      <div
        className="px-2 py-3 border-t"
        style={{ borderColor: "var(--color-border-subtle)" }}
      >
        {/* Language Toggle */}
        <button
          onClick={toggleLanguage}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors duration-150"
          style={{ color: "var(--color-ink-tertiary)" }}
          title={language === "zh" ? t.common.english : t.common.chinese}
        >
          <Globe className="w-[18px] h-[18px]" />
          {!isCollapsed && (
            <span className="font-body text-sm">
              {language === "zh" ? t.common.english : t.common.chinese}
            </span>
          )}
        </button>

        {/* Collapse Toggle */}
        <button
          onClick={toggleSidebar}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors duration-150 mt-1"
          style={{ color: "var(--color-ink-tertiary)" }}
        >
          {isCollapsed ? (
            <ChevronRight className="w-[18px] h-[18px]" />
          ) : (
            <>
              <ChevronLeft className="w-[18px] h-[18px]" />
              <span className="font-body text-sm">{t.common.collapse}</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
