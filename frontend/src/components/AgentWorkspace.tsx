import { useState } from "react";
import { PanelLeft, PanelRight } from "lucide-react";
import TodoPanel from "./TodoPanel";
import ExecutionTrace from "./ExecutionTrace";
import FileExplorer from "./FileExplorer";
import HumanInTheLoop from "./HumanInTheLoop";

interface Props {
  children: React.ReactNode;
}

export default function AgentWorkspace({ children }: Props) {
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(false);

  return (
    <div className="h-full flex">
      {leftOpen && (
        <aside className="w-72 flex-shrink-0 border-r border-[#E8E4DC] bg-[#FAFAF7] overflow-y-auto">
          <TodoPanel />
          <ExecutionTrace />
        </aside>
      )}

      <main className="flex-1 flex flex-col min-w-0 relative">
        <div className="absolute top-2 left-2 z-10 flex gap-1">
          <button
            onClick={() => setLeftOpen(!leftOpen)}
            className="p-1.5 rounded bg-white shadow-sm border border-[#E8E4DC] hover:bg-[#F5F0E8]"
            title="Toggle sidebar"
          >
            <PanelLeft className="w-4 h-4 text-[#8b4513]" />
          </button>
        </div>
        <div className="absolute top-2 right-2 z-10">
          <button
            onClick={() => setRightOpen(!rightOpen)}
            className="p-1.5 rounded bg-white shadow-sm border border-[#E8E4DC] hover:bg-[#F5F0E8]"
            title="Toggle file panel"
          >
            <PanelRight className="w-4 h-4 text-[#8b4513]" />
          </button>
        </div>

        {children}
        <HumanInTheLoop />
      </main>

      {rightOpen && (
        <aside className="w-64 flex-shrink-0 border-l border-[#E8E4DC] bg-[#FAFAF7] overflow-y-auto">
          <FileExplorer />
        </aside>
      )}
    </div>
  );
}
