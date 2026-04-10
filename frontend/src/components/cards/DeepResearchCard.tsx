// frontend/src/components/cards/DeepResearchCard.tsx
import { useState } from "react";
import { ChevronDown, ChevronUp, BookOpen, Lightbulb } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { removeThinkingTags } from "../../lib/textUtils";

interface Props {
  data: {
    report: string;
    dimensions?: string[];
    findings?: Record<string, string>;
  };
  onAction?: (text: string) => void;
}

export default function DeepResearchCard({ data }: Props) {
  const [expandedDimensions, setExpandedDimensions] = useState<Set<number>>(
    new Set()
  );

  if (!data) {
    return (
      <div
        className="my-2 p-4 rounded-xl"
        style={{
          background: "rgba(184, 134, 11, 0.04)",
          border: "1px solid rgba(184, 134, 11, 0.2)",
          color: "var(--color-ink-secondary)",
        }}
      >
        <p className="font-body text-sm">深入研究数据为空</p>
      </div>
    );
  }

  const toggleDimension = (index: number) => {
    setExpandedDimensions((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const dimensions = data.dimensions || [];
  const findings = data.findings || {};

  return (
    <div
      className="card-academic overflow-hidden animate-slide-up"
      style={{
        background:
          "linear-gradient(135deg, rgba(250, 248, 245, 0.95) 0%, rgba(245, 240, 232, 0.92) 100%)",
        border: "1px solid rgba(232, 223, 208, 0.8)",
        boxShadow:
          "0 2px 8px rgba(44, 24, 16, 0.06), 0 1px 3px rgba(44, 24, 16, 0.08)",
      }}
    >
      {/* Header */}
      <div
        className="px-5 py-4 border-b border-academic-border"
        style={{
          background:
            "linear-gradient(135deg, rgba(107, 68, 35, 0.06) 0%, rgba(154, 107, 60, 0.04) 100%)",
        }}
      >
        <div className="flex items-center gap-2">
          <BookOpen
            className="w-5 h-5"
            style={{ color: "var(--color-accent)" }}
          />
          <h3 className="font-display text-base font-medium text-academic-sepia">
            深入研究报告
          </h3>
        </div>
        {dimensions.length > 0 && (
          <p className="mt-1 text-xs text-academic-muted font-mono">
            {dimensions.length} 个研究维度
          </p>
        )}
      </div>

      {/* 综合报告 */}
      {data.report && (
        <div className="p-5 border-b border-academic-border">
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb
              className="w-4 h-4"
              style={{ color: "var(--color-amber)" }}
            />
            <span className="font-body text-sm font-medium text-academic-sepia">
              综合结论
            </span>
          </div>
          <div className="font-body text-sm text-academic-ink leading-relaxed prose-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {removeThinkingTags(data.report)}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {/* 各维度发现 */}
      {dimensions.length > 0 && (
        <div className="p-4 space-y-3">
          <span className="text-xs text-academic-muted font-mono uppercase tracking-wider">
            各维度分析
          </span>
          {dimensions.map((dim, index) => (
            <div
              key={index}
              className="border border-academic-border rounded-medium overflow-hidden transition-all duration-200"
              style={{
                background: expandedDimensions.has(index)
                  ? "linear-gradient(135deg, rgba(184, 134, 11, 0.03) 0%, rgba(212, 160, 18, 0.02) 100%)"
                  : "rgba(245, 240, 232, 0.01)",
              }}
            >
              <button
                onClick={() => toggleDimension(index)}
                className="w-full px-4 py-3 flex items-center justify-between text-left transition-colors hover:bg-academic-paper/30"
              >
                <span className="font-body text-sm font-medium text-academic-sepia">
                  {dim}
                </span>
                {expandedDimensions.has(index) ? (
                  <ChevronUp className="w-4 h-4 text-academic-muted flex-shrink-0" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-academic-muted flex-shrink-0" />
                )}
              </button>
              {expandedDimensions.has(index) && findings[dim] && (
                <div className="px-4 pb-4 pt-2 animate-slide-down">
                  <div className="font-body text-sm text-academic-ink/90 leading-relaxed prose-content">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {removeThinkingTags(findings[dim])}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
