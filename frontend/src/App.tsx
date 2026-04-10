import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Papers from "./pages/Papers";
import ConceptsGraph from "./pages/ConceptsGraph";
import Chat from "./pages/Chat";
import Settings from "./pages/Settings";
import Sidebar from "./components/Sidebar";
import ResearchAgentBubble from "./components/ResearchAgentBubble";

function App() {
  return (
    <BrowserRouter>
      <div
        className="h-screen flex overflow-hidden"
        style={{ background: "var(--color-cream)" }}
      >
        {/* Left Sidebar */}
        <Sidebar />

        {/* Main Content Area */}
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/concepts" element={<ConceptsGraph />} />
            <Route path="/papers" element={<Papers />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>

        {/* Global Research Agent Bubble - only show on concepts page */}
        <ResearchAgentBubble />
      </div>
    </BrowserRouter>
  );
}

export default App;
