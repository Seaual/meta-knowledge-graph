import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import Papers from './pages/Papers'
import ConceptsGraph from './pages/ConceptsGraph'

function App() {
  return (
    <BrowserRouter>
      <div className="h-screen flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white shadow-sm border-b flex-shrink-0">
          <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
            <Link to="/" className="text-xl font-bold text-gray-900">
              Meta Knowledge Graph
            </Link>
            <nav className="flex gap-6">
              <Link to="/" className="text-gray-600 hover:text-gray-900">
                Home
              </Link>
              <Link to="/papers" className="text-gray-600 hover:text-gray-900">
                Papers
              </Link>
              <Link to="/concepts" className="text-gray-600 hover:text-gray-900">
                Concepts
              </Link>
            </nav>
          </div>
        </header>

        {/* Main Content - fill remaining height */}
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