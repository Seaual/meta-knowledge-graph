import { Bot } from "lucide-react";

interface Props {
  name: string;
  status: "running" | "completed";
}

const LABELS: Record<string, string> = {
  "citation-analyst": "引用分析",
  "research-discoverer": "研究点发现",
  "paper-qa": "论文问答",
  "deep-researcher": "深度研究",
};

export default function SubagentBadge({ name, status }: Props) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-[#4a6b8a12] text-[#4a6b8a]">
        <Bot className="w-3 h-3" />
        {LABELS[name] || name}
        {status === "running" && (
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
        )}
      </span>
    </div>
  );
}
