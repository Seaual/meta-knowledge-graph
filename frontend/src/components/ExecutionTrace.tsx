import { useState } from "react";
import { ChevronDown, ChevronUp, Wrench, Bot } from "lucide-react";
import { useAgentStore } from "../stores/agentStore";

export default function ExecutionTrace() {
  const steps = useAgentStore((s) => s.executionSteps);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (steps.length === 0) return null;

  return (
    <div className="p-4">
      <h3 className="font-display text-sm font-medium mb-3 text-[#5a3e28]">
        执行轨迹
      </h3>
      <div className="space-y-1">
        {steps.map((step) => (
          <div key={step.id} className="rounded bg-[#F5F0E8] text-xs">
            <button
              onClick={() => toggle(step.id)}
              className="w-full px-2 py-1.5 flex items-center gap-2"
            >
              {step.type === "tool_call" || step.type === "tool_result" ? (
                <Wrench className="w-3 h-3 text-[#8b4513]" />
              ) : (
                <Bot className="w-3 h-3 text-[#4a6b8a]" />
              )}
              <span className="text-[#2c1810]">{step.name}</span>
              {step.args || step.result ? (
                expanded.has(step.id) ? <ChevronUp className="w-3 h-3 ml-auto" /> : <ChevronDown className="w-3 h-3 ml-auto" />
              ) : null}
            </button>
            {expanded.has(step.id) && (
              <div className="px-2 pb-1.5 space-y-1">
                {step.args && (
                  <pre className="bg-white p-1 rounded overflow-x-auto">
                    {JSON.stringify(step.args, null, 2)}
                  </pre>
                )}
                {step.result && (
                  <pre className="bg-white p-1 rounded overflow-x-auto text-green-700">
                    {step.result}
                  </pre>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
