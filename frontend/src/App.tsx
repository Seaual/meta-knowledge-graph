import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import Papers from './pages/Papers'
import Concepts from './pages/Concepts'
import Graph from './pages/Graph'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            <Link to="/" className="text-xl font-bold text-gray-900">
              OpenClaw
            </Link>
            <nav className="flex gap-6">
              <Link to="/" className="text-gray-600 hover:text-gray-900">
                首页
              </Link>
              <Link to="/papers" className="text-gray-600 hover:text-gray-900">
                论文
              </Link>
              <Link to="/concepts" className="text-gray-600 hover:text-gray-900">
                概念
              </Link>
              <Link to="/graph" className="text-gray-600 hover:text-gray-900">
                图谱
              </Link>
            </nav>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/papers" element={<Papers />} />
            <Route path="/concepts" element={<Concepts />} />
            <Route path="/graph" element={<Graph />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App