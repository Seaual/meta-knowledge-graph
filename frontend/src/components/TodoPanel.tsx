import { useState } from "react";
import { ChevronDown, ChevronUp, Loader2, CheckCircle, XCircle, Circle } from "lucide-react";
import { useAgentStore } from "../stores/agentStore";

export default function TodoPanel() {
  const todos = useAgentStore((s) => s.todos);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <Loader2 className="w-4 h-4 animate-spin text-amber-600" />;
      case "completed":
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case "failed":
        return <XCircle className="w-4 h-4 text-red-600" />;
      default:
        return <Circle className="w-4 h-4 text-gray-400" />;
    }
  };

  if (todos.length === 0) return null;

  return (
    <div className="p-4 border-b border-[#E8E4DC]">
      <h3 className="font-display text-sm font-medium mb-3 text-[#5a3e28]">
        执行计划
      </h3>
      <div className="space-y-2">
        {todos.map((todo) => (
          <div key={todo.id} className="rounded-lg bg-[#FAFAF7] border border-[#E8E4DC]">
            <button
              onClick={() => toggle(todo.id)}
              className="w-full px-3 py-2 flex items-center gap-2 text-sm"
            >
              {statusIcon(todo.status)}
              <span className={todo.status === "completed" ? "text-gray-500 line-through" : "text-[#2c1810]"}>
                {todo.title}
              </span>
              {todo.detail && (
                expanded.has(todo.id) ? <ChevronUp className="w-3 h-3 ml-auto" /> : <ChevronDown className="w-3 h-3 ml-auto" />
              )}
            </button>
            {expanded.has(todo.id) && todo.detail && (
              <div className="px-3 pb-2 text-xs text-[#6b5d4f] border-t border-[#E8E4DC]">
                {todo.detail}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
