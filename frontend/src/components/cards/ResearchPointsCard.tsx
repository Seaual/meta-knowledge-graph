// frontend/src/components/cards/ResearchPointsCard.tsx
import { useState } from "react";
import { ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import { removeThinkingTags } from "../../lib/textUtils";
import { useTranslation } from "../../i18n";

interface ResearchPoint {
  title: string;
  hypothesis?: string;
  description: string;
  discovery_method?: string;
  difficulty_reason?: string;
  rationale?: string;
  related_concepts?: string[];
  difficulty?: string;
  novelty?: string;
  potential_impact?: string;
}

interface AnalysisContext {
  concept?: {
    id: string;
    name?: string;
    text?: string;
    category?: string;
    paper_count?: number;
  };
  ancestors?: Array<{ id: string; name?: string; text?: string }>;
  descendants?: Array<{
    id: string;
    name?: string;
    text?: string;
    depth?: number;
  }>;
  siblings?: Array<{ id: string; name?: string; text?: string }>;
  edge_nodes?: Array<{ id: string; name?: string; text?: string }>;
  related_papers?: Array<{
    title: string;
    abstract?: string;
    keywords?: string[];
  }>;
}

interface Props {
  data: {
    concept_name: string;
    research_points: ResearchPoint[];
    analysis_context?: AnalysisContext;
  };
  onAction: (text: string) => void;
}

// Color mapping for difficulty, novelty, and impact
const RATING_COLORS: Record<string, string> = {
  low: "#4a6b8a", // slate blue
  medium: "#b8860b", // amber
  high: "#c2410c", // terracotta
};

// Get display label for discovery method
function getMethodLabel(method: string, t: ReturnType<typeof useTranslation>["t"]): string {
  if (!method) return t.common.unknownMethod;
  return (t.concepts.researchPoints.method as Record<string, string>)[method] || method;
}

// Research point item component
function ResearchPointItem({
  point,
  index,
  isExpanded,
  onToggle,
  onAction,
  t,
}: {
  point: ResearchPoint;
  index: number;
  isExpanded: boolean;
  onToggle: () => void;
  onAction: (text: string) => void;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  const handleDeepResearch = () => {
    onAction(`深入研究「${point.title}」这个研究方向`);
  };

  return (
    <div
      className="border border-academic-border rounded-medium overflow-hidden transition-all duration-200"
      style={{
        background: isExpanded
          ? "linear-gradient(135deg, rgba(184, 134, 11, 0.03) 0%, rgba(212, 160, 18, 0.02) 100%)"
          : "rgba(245, 240, 232, 0.01)",
      }}
    >
      {/* Header - clickable */}
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-start gap-3 text-left transition-colors hover:bg-academic-paper/30"
      >
        {/* Number badge */}
        <span
          className="flex-shrink-0 w-6 h-6 rounded-soft flex items-center justify-center font-mono text-xs font-medium"
          style={{
            background:
              "linear-gradient(135deg, rgba(184, 134, 11, 0.12) 0%, rgba(212, 160, 18, 0.08) 100%)",
            color: "#6b4423",
          }}
        >
          {index + 1}
        </span>

        {/* Title and preview */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-display text-sm font-medium text-academic-sepia truncate">
              {removeThinkingTags(point.title)}
            </span>
            {/* Expand/collapse icon */}
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-academic-muted flex-shrink-0" />
            ) : (
              <ChevronDown className="w-4 h-4 text-academic-muted flex-shrink-0" />
            )}
          </div>

          {/* Hypothesis preview when collapsed */}
          {!isExpanded && point.hypothesis && (
            <p className="mt-1 text-xs text-academic-muted line-clamp-1 italic">
              {removeThinkingTags(point.hypothesis)}
            </p>
          )}
        </div>

        {/* Rating badges */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {point.difficulty && (
            <span
              className="px-1.5 py-0.5 rounded-soft text-[10px] font-medium"
              style={{
                background: RATING_COLORS[point.difficulty.toLowerCase()] || RATING_COLORS.medium,
                color: "#fff",
              }}
              title={`难度`}
            >
              难度{point.difficulty === "low" ? "·低" : point.difficulty === "medium" ? "·中" : "·高"}
            </span>
          )}
          {point.novelty && (
            <span
              className="px-1.5 py-0.5 rounded-soft text-[10px] font-medium"
              style={{
                background: RATING_COLORS[point.novelty.toLowerCase()] || RATING_COLORS.medium,
                color: "#fff",
              }}
              title={`新颖度`}
            >
              新颖{point.novelty === "incremental" ? "·渐进" : point.novelty === "moderate" ? "·中等" : "·高"}
            </span>
          )}
          {point.potential_impact && (
            <span
              className="px-1.5 py-0.5 rounded-soft text-[10px] font-medium"
              style={{
                background: RATING_COLORS[point.potential_impact.toLowerCase()] || RATING_COLORS.medium,
                color: "#fff",
              }}
              title={`潜在影响`}
            >
              影响{point.potential_impact === "niche" ? "·局部" : point.potential_impact === "broad" ? "·广泛" : "·变革"}
            </span>
          )}
        </div>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pb-4 pt-2 animate-slide-down">
          {/* Full description */}
          <div className="mb-3">
            <p className="font-body text-sm text-academic-ink leading-relaxed">
              {removeThinkingTags(point.description)}
            </p>
          </div>

          {/* Hypothesis */}
          {point.hypothesis && (
            <div className="mb-3 p-2.5 rounded-soft bg-academic-vellum/50 border border-academic-border/50">
              <span className="text-xs text-academic-muted font-mono uppercase tracking-wider">
                假设
              </span>
              <p className="mt-1 font-quote text-sm text-academic-sepia italic">
                {removeThinkingTags(point.hypothesis)}
              </p>
            </div>
          )}

          {/* Discovery method */}
          {point.discovery_method && (
            <div className="mb-3 flex items-center gap-2">
              <span className="text-xs text-academic-muted font-mono uppercase tracking-wider">
                发现方法
              </span>
              <span
                className="px-2 py-0.5 rounded-soft text-xs font-medium"
                style={{
                  background: "rgba(184, 134, 11, 0.08)",
                  color: "#6b4423",
                }}
              >
                {getMethodLabel(point.discovery_method, t)}
              </span>
            </div>
          )}

          {/* Difficulty reason */}
          {point.difficulty_reason && (
            <div className="mb-3">
              <span className="text-xs text-academic-muted font-mono uppercase tracking-wider">
                难度依据
              </span>
              <p className="mt-1 font-body text-sm text-academic-ink/80">
                {removeThinkingTags(point.difficulty_reason)}
              </p>
            </div>
          )}

          {/* Rationale */}
          {point.rationale && (
            <div className="mb-3">
              <span className="text-xs text-academic-muted font-mono uppercase tracking-wider">
                推理依据
              </span>
              <p className="mt-1 font-body text-sm text-academic-ink/80">
                {removeThinkingTags(point.rationale)}
              </p>
            </div>
          )}

          {/* Related concepts */}
          {point.related_concepts && point.related_concepts.length > 0 && (
            <div className="mb-3">
              <span className="text-xs text-academic-muted font-mono uppercase tracking-wider">
                相关概念
              </span>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {point.related_concepts.map((concept, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 rounded-soft text-xs font-medium"
                    style={{
                      background: "rgba(154, 107, 60, 0.08)",
                      color: "#9a6b3c",
                      border: "1px solid rgba(154, 107, 60, 0.15)",
                    }}
                  >
                    {removeThinkingTags(concept)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Deep research button */}
          <button
            onClick={handleDeepResearch}
            className="mt-3 flex items-center gap-2 px-3 py-2 rounded-medium text-sm font-medium transition-all hover:shadow-glow-amber"
            style={{
              background: "linear-gradient(135deg, #b8860b 0%, #d4a012 100%)",
              color: "#fffef9",
            }}
          >
            <Sparkles className="w-4 h-4" />
            深入研究此方向
          </button>
        </div>
      )}
    </div>
  );
}

export default function ResearchPointsCard({ data, onAction }: Props) {
  const { t } = useTranslation();
  const [expandedPoints, setExpandedPoints] = useState<Set<number>>(new Set());

  // 调试日志
  console.log("ResearchPointsCard data:", data);

  // 防御性检查
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
        <p className="font-body text-sm">研究点数据为空</p>
      </div>
    );
  }

  if (!data.research_points) {
    return (
      <div
        className="my-2 p-4 rounded-xl"
        style={{
          background: "rgba(184, 134, 11, 0.04)",
          border: "1px solid rgba(184, 134, 11, 0.2)",
          color: "var(--color-ink-secondary)",
        }}
      >
        <p className="font-body text-sm">
          {t.common.researchDataError}
        </p>
        <p className="font-mono text-xs mt-2 opacity-70">
          收到的数据: {JSON.stringify(Object.keys(data))}
        </p>
      </div>
    );
  }

  if (!Array.isArray(data.research_points)) {
    return (
      <div
        className="my-2 p-4 rounded-xl"
        style={{
          background: "rgba(180, 60, 60, 0.05)",
          border: "1px solid rgba(180, 60, 60, 0.2)",
          color: "#8b4040",
        }}
      >
        <p className="font-body text-sm">research_points 不是数组</p>
        <p className="font-mono text-xs mt-2 opacity-70">
          类型: {typeof data.research_points}
        </p>
      </div>
    );
  }

  const togglePoint = (index: number) => {
    setExpandedPoints((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const expandAll = () => {
    if (!data?.research_points) return;
    setExpandedPoints(new Set(data.research_points.map((_, i) => i)));
  };

  const collapseAll = () => {
    setExpandedPoints(new Set());
  };

  const allExpanded =
    data.research_points && expandedPoints.size === data.research_points.length;
  const hasContext =
    data.analysis_context &&
    (data.analysis_context.ancestors ||
      data.analysis_context.descendants ||
      data.analysis_context.edge_nodes);
  const conceptName = data.concept_name || t.common.unnamedConcept;

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
            "linear-gradient(135deg, rgba(184, 134, 11, 0.04) 0%, rgba(212, 160, 18, 0.02) 100%)",
        }}
      >
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-display text-base font-medium text-academic-sepia">
              {conceptName}
            </h3>
            <p className="mt-1 text-xs text-academic-muted font-mono">
              {data.research_points.length} 个研究点
            </p>
          </div>

          {/* Expand/collapse all buttons */}
          {data.research_points.length > 1 && (
            <div className="flex items-center gap-2">
              <button
                onClick={allExpanded ? collapseAll : expandAll}
                className="text-xs text-academic-muted hover:text-academic-amber transition-colors font-mono"
              >
                {allExpanded ? t.common.collapseAll : t.common.expandAll}
              </button>
            </div>
          )}
        </div>

        {/* Analysis context stats */}
        {hasContext && (
          <div className="mt-3 flex items-center gap-4">
            {data.analysis_context!.ancestors &&
              data.analysis_context!.ancestors.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-academic-muted">上游概念</span>
                  <span
                    className="px-1.5 py-0.5 rounded-soft text-xs font-mono font-medium"
                    style={{
                      background: "rgba(107, 68, 35, 0.08)",
                      color: "#6b4423",
                    }}
                  >
                    {data.analysis_context!.ancestors!.length}
                  </span>
                </div>
              )}
            {data.analysis_context!.descendants &&
              data.analysis_context!.descendants.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-academic-muted">下游概念</span>
                  <span
                    className="px-1.5 py-0.5 rounded-soft text-xs font-mono font-medium"
                    style={{
                      background: "rgba(184, 134, 11, 0.08)",
                      color: "#b8860b",
                    }}
                  >
                    {data.analysis_context!.descendants!.length}
                  </span>
                </div>
              )}
            {data.analysis_context!.edge_nodes &&
              data.analysis_context!.edge_nodes.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-academic-muted">边缘节点</span>
                  <span
                    className="px-1.5 py-0.5 rounded-soft text-xs font-mono font-medium"
                    style={{
                      background: "rgba(154, 107, 60, 0.08)",
                      color: "#9a6b3c",
                    }}
                  >
                    {data.analysis_context!.edge_nodes!.length}
                  </span>
                </div>
              )}
          </div>
        )}
      </div>

      {/* Research points list */}
      <div className="p-4 space-y-3">
        {data.research_points.length === 0 ? (
          <div className="text-center py-6">
            <p className="text-sm text-academic-muted">{t.common.noResearchPoints}</p>
          </div>
        ) : (
          data.research_points.map((point, index) => (
            <ResearchPointItem
              key={index}
              point={point}
              index={index}
              isExpanded={expandedPoints.has(index)}
              onToggle={() => togglePoint(index)}
              onAction={onAction}
              t={t}
            />
          ))
        )}
      </div>
    </div>
  );
}
