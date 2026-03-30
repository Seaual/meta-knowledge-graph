import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Globe } from 'lucide-react'
import Home from './pages/Home'
import Papers from './pages/Papers'
import ConceptsGraph from './pages/ConceptsGraph'
import { useTranslation } from './i18n'

// Navigation link component with active state
function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  const location = useLocation()
  const isActive = location.pathname === to

  return (
    <Link
      to={to}
      className={`nav-link ${isActive ? 'active' : ''}`}
    >
      {children}
    </Link>
  )
}

// Language switcher component
function LanguageSwitcher() {
  const { language, toggleLanguage } = useTranslation()

  return (
    <button
      onClick={toggleLanguage}
      className="flex items-center gap-2 px-3 py-1.5 rounded-medium bg-paper border border-academic text-sm text-muted hover:text-sepia hover:border-sepia transition-all"
      title={language === 'zh' ? 'Switch to English' : '切换到中文'}
    >
      <Globe className="w-4 h-4" />
      <span className="font-body font-medium">{language === 'zh' ? 'EN' : '中'}</span>
    </button>
  )
}

function App() {
  const { t } = useTranslation()

  return (
    <BrowserRouter>
      <div className="h-screen flex flex-col overflow-hidden bg-gradient-warm">
        {/* Header - Academic Style */}
        <header className="header-academic flex-shrink-0">
          <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 group">
              <div className="w-8 h-8 rounded-md bg-gradient-amber flex items-center justify-center shadow-paper group-hover:shadow-glow-amber transition-all duration-250">
                <span className="font-display text-white text-lg font-semibold">M</span>
              </div>
              <span className="font-display text-xl font-medium text-sepia group-hover:text-amber transition-colors">
                Meta Knowledge Graph
              </span>
            </Link>

            {/* Navigation & Language */}
            <div className="flex items-center gap-4">
              <nav className="flex gap-2">
                <NavLink to="/">{t.nav.home}</NavLink>
                <NavLink to="/papers">{t.nav.papers}</NavLink>
                <NavLink to="/concepts">{t.nav.concepts}</NavLink>
              </nav>
              <LanguageSwitcher />
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/papers" element={<Papers />} />
            <Route path="/concepts" element={<ConceptsGraph />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App