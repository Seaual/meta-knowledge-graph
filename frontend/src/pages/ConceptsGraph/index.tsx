// frontend/src/pages/ConceptsGraph/index.tsx
// Knowledge Graph - Academic Style Force Graph with Papers

import { useEffect, useRef, useState, useCallback } from "react";
import ForceGraph from "force-graph";
import { forceManyBody, forceLink, forceCollide, forceCenter } from "d3-force";
import { exportApi } from "../../lib/api";
import {
  Download,
  ChevronDown,
  Folder,
  Search,
  X,
  ArrowLeft,
} from "lucide-react";
import DedupPanel from "../../components/DedupPanel";
import FilterPanel from "../../components/FilterPanel";
import RecommendationPanel from "../../components/RecommendationPanel";
import { useTranslation } from "../../i18n";
import { useGraph } from "./hooks/useGraph";
import {
  CATEGORY_COLORS,
  PAPER_COLOR,
  CENTER_COLOR,
  CATEGORY_SIZES,
  CATEGORY_RADII,
  DEFAULT_CATEGORIES,
} from "./constants";
import type { Concept, GraphNode } from "./types";

export default function ConceptsGraph() {
  const { t, language } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);

  // Get state and actions from useGraph hook
  const {
    loading,
    concepts,
    graphNodes,
    graphLinks,
    folders,
    viewMode,
    selectedConcept,
    selectedPaper,
    activeFolder,
    forceStrength,
    setForceStrength,
    researchPoints,
    loadingResearchPoints,
    handleConceptClick,
    handlePaperClick,
    handleViewPapers,
    handleBack,
    handleDiscoverResearchPoints,
    setActiveFolder,
    setSelectedConcept,
    setSelectedPaper,
  } = useGraph();

  // UI state (kept in component)
  const [dedupOpen, setDedupOpen] = useState(false);
  const [filterPanelOpen, setFilterPanelOpen] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showFolderMenu, setShowFolderMenu] = useState(false);
  const [showConceptActions, setShowConceptActions] = useState(false);
  const [showResearchPanel, setShowResearchPanel] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategories, setSelectedCategories] =
    useState<string[]>(DEFAULT_CATEGORIES);
  const [highlightedNodeId, setHighlightedNodeId] = useState<string | null>(
    null
  );
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null);
  const [recommendationPanelOpen, setRecommendationPanelOpen] = useState(false);
  const [
    selectedConceptsForRecommendation,
    setSelectedConceptsForRecommendation,
  ] = useState<Concept[]>([]);
  const [isSelectingForRecommendation, setIsSelectingForRecommendation] =
    useState(false);
  const searchQueryRef = useRef(searchQuery);
  const selectedCategoriesRef = useRef(selectedCategories);
  const highlightedNodeIdRef = useRef(highlightedNodeId);
  const selectingForRecommendationRef = useRef(isSelectingForRecommendation);
  const selectedRecommendationConceptsRef = useRef(
    selectedConceptsForRecommendation
  );
  const languageRef = useRef(language);
  const viewModeRef = useRef(viewMode);

  useEffect(() => {
    searchQueryRef.current = searchQuery;
    selectedCategoriesRef.current = selectedCategories;
    highlightedNodeIdRef.current = highlightedNodeId;
    selectingForRecommendationRef.current = isSelectingForRecommendation;
    selectedRecommendationConceptsRef.current =
      selectedConceptsForRecommendation;
    languageRef.current = language;
    viewModeRef.current = viewMode;
    graphRef.current?.refresh();
  }, [
    searchQuery,
    selectedCategories,
    highlightedNodeId,
    isSelectingForRecommendation,
    selectedConceptsForRecommendation,
    language,
    viewMode,
  ]);

  // Filter handlers (UI callbacks)
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
  }, []);

  const handleCategoryChange = useCallback((categories: string[]) => {
    setSelectedCategories(categories);
  }, []);

  const handleFocusNode = useCallback(
    (nodeId: string) => {
      const node = graphNodes.find((n) => n.id === nodeId);
      if (node && graphRef.current) {
        graphRef.current.centerAt(node.x, node.y, 1000);
        graphRef.current.zoom(2, 1000);
        setHighlightedNodeId(nodeId);
        setTimeout(() => setHighlightedNodeId(null), 2000);
      }
    },
    [graphNodes]
  );

  // Recommendation handlers (UI callbacks)
  const handleAddConceptToRecommendation = useCallback((concept: Concept) => {
    setSelectedConceptsForRecommendation((prev) => {
      if (prev.some((c) => c.id === concept.id)) return prev;
      return [...prev, concept];
    });
  }, []);

  const handleRemoveConceptFromRecommendation = useCallback(
    (conceptId: string) => {
      setSelectedConceptsForRecommendation((prev) =>
        prev.filter((c) => c.id !== conceptId)
      );
    },
    []
  );

  const handleStartRecommendationSelection = useCallback(() => {
    if (selectedConcept) {
      setSelectedConceptsForRecommendation([selectedConcept]);
    }
    setIsSelectingForRecommendation(true);
    setShowConceptActions(false);
    setRecommendationPanelOpen(true);
  }, [selectedConcept]);

  const handleToggleConceptInRecommendation = useCallback(
    (conceptId: string) => {
      const concept = concepts.find((c) => c.id === conceptId);
      if (!concept) return;

      setSelectedConceptsForRecommendation((prev) => {
        if (prev.some((c) => c.id === conceptId)) {
          return prev.filter((c) => c.id !== conceptId);
        }
        return [
          ...prev,
          {
            id: concept.id,
            text: concept.text,
            text_en: concept.text_en,
            category: concept.category,
            paper_count: concept.paper_count,
          },
        ];
      });
    },
    [concepts]
  );

  // Export handlers (UI callbacks)
  const handleExportMarkdown = useCallback(async () => {
    try {
      const res = await exportApi.download(activeFolder || undefined);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `knowledge-graph-${new Date().toISOString().split("T")[0]}.md`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
      alert("Export failed");
    }
  }, [activeFolder]);

  const handleExportCanvas = useCallback(async () => {
    try {
      const res = await exportApi.downloadCanvas(activeFolder || undefined);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `knowledge-graph-${new Date().toISOString().split("T")[0]}.canvas`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Canvas export failed:", err);
      alert("Export failed");
    }
  }, [activeFolder]);

  const handleExportHtml = useCallback(async () => {
    try {
      const res = await exportApi.downloadHtml(activeFolder || undefined);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `knowledge-graph-${new Date().toISOString().split("T")[0]}.html`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("HTML export failed:", err);
      alert("Export failed");
    }
  }, [activeFolder]);

  // Initialize ForceGraph once, then update data and paint state separately.
  useEffect(() => {
    if (!containerRef.current || graphRef.current) return;

    const graph = new ForceGraph(containerRef.current!)
      .nodeId("id")
      .nodeLabel((node: any) => {
        if (languageRef.current === "en" && node.name_en) {
          return node.name_en;
        }
        return node.name;
      })
      .nodeVal((node: any) => {
        if (node.type === "center") return 3;
        if (node.type === "paper") return 1.5;
        return 1 + Math.sqrt(node.paperCount || 0) * 0.3;
      })
      .nodeCanvasObject(
        (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const isPaper = node.type === "paper";
          const isCenter = node.type === "center";
          const isSelectedForRecommendation =
            selectingForRecommendationRef.current &&
            selectedRecommendationConceptsRef.current.some(
              (concept) => concept.id === node.id
            );

          let size: number;
          let color: string;

          if (isCenter) {
            size = 20;
            color = CENTER_COLOR;
          } else if (isPaper) {
            size = 8;
            color = PAPER_COLOR;
          } else {
            const baseSize = CATEGORY_SIZES[node.category || "method"] || 10;
            size = baseSize + Math.sqrt(node.paperCount || 0) * 0.3;
            color = CATEGORY_COLORS[node.category || "method"] || "#8a7a6a";
          }

          let opacity = 1;
          const searchValue = searchQueryRef.current;
          if (searchValue) {
            const searchLower = searchValue.toLowerCase();
            const matchesSearch =
              node.name.toLowerCase().includes(searchLower) ||
              (node.name_en &&
                node.name_en.toLowerCase().includes(searchLower));
            opacity = matchesSearch ? 1 : 0.2;
          } else if (
            node.category &&
            !selectedCategoriesRef.current.includes(node.category)
          ) {
            opacity = 0.15;
          }

          if (highlightedNodeIdRef.current === node.id) {
            opacity = 1;
          }

          const x = node.x || 0;
          const y = node.y || 0;

          if (highlightedNodeIdRef.current === node.id) {
            ctx.beginPath();
            ctx.arc(x, y, size + 8, 0, 2 * Math.PI);
            ctx.fillStyle = "rgba(184, 134, 11, 0.4)";
            ctx.fill();
          }

          if (isSelectedForRecommendation) {
            ctx.beginPath();
            ctx.arc(x, y, size + 6, 0, 2 * Math.PI);
            ctx.fillStyle = "rgba(45, 90, 39, 0.4)";
            ctx.fill();
            ctx.beginPath();
            ctx.arc(x + size * 0.7, y - size * 0.7, 4, 0, 2 * Math.PI);
            ctx.fillStyle = "#2d5a27";
            ctx.fill();
            ctx.beginPath();
            ctx.arc(x + size * 0.7, y - size * 0.7, 2, 0, 2 * Math.PI);
            ctx.fillStyle = "#ffffff";
            ctx.fill();
          }

          ctx.globalAlpha = opacity;
          ctx.beginPath();
          ctx.arc(x, y, size, 0, 2 * Math.PI);

          if (isPaper) {
            ctx.fillStyle = color + "40";
            ctx.fill();
            ctx.strokeStyle = color;
            ctx.lineWidth = 2.5;
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(x, y, size * 0.35, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          } else if (isCenter) {
            const gradient = ctx.createRadialGradient(x, y, 0, x, y, size);
            gradient.addColorStop(0, color + "60");
            gradient.addColorStop(1, color + "20");
            ctx.fillStyle = gradient;
            ctx.fill();
            ctx.strokeStyle = color;
            ctx.lineWidth = 3;
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(x, y, size * 0.5, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          } else {
            ctx.fillStyle = color + "30";
            ctx.fill();
            ctx.strokeStyle = color;
            ctx.lineWidth = 2 / globalScale;
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(x, y, size * 0.3, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }

          if (globalScale > 0.5) {
            const fontSize = isCenter ? 14 : 11;
            ctx.font = `${fontSize / globalScale}px 'Source Sans 3', sans-serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillStyle = "#2c1810";
            const displayName =
              languageRef.current === "en" && node.name_en
                ? node.name_en
                : node.name;
            const label =
              displayName && displayName.length > 30
                ? displayName.substring(0, 30) + "..."
                : displayName || "";
            ctx.fillText(label, x, y + size + 4 / globalScale);
          }

          ctx.globalAlpha = 1;
        }
      )
      .linkColor((link: any) => {
        const source = link.source;
        if (source.type === "center") return PAPER_COLOR + "60";
        return "#d4c4b0";
      })
      .linkWidth((link: any) => {
        const source = link.source;
        return source.type === "center" ? 2 : 1;
      })
      .linkDirectionalParticles((link: any) => {
        const source = link.source;
        return source.type === "center" ? 3 : 2;
      })
      .linkDirectionalParticleWidth(2)
      .linkDirectionalParticleColor(() => "#b8860b")
      .d3AlphaDecay(0.02)
      .d3VelocityDecay(0.3)
      .d3Force(
        "charge",
        forceManyBody().strength((node: any) => {
          if (node.type === "paper") return -forceStrength * 0.3;
          if (node.type === "center") return -forceStrength * 1.5;
          const depthBonus = -(node.depth || 0) * 20;
          return -forceStrength * 0.6 + depthBonus;
        })
      )
      .d3Force(
        "center",
        forceCenter(
          containerRef.current?.clientWidth
            ? containerRef.current.clientWidth / 2
            : 500,
          containerRef.current?.clientHeight
            ? containerRef.current.clientHeight / 2
            : 400
        )
      )
      .d3Force(
        "link",
        forceLink()
          .id((d: any) => d.id)
          .distance(50)
          .strength(0.6)
      )
      .d3Force(
        "collision",
        forceCollide().radius((node: any) => {
          if (node.type === "paper") return 12;
          if (node.type === "center") return 25;
          return CATEGORY_RADII[node.category || "method"] || 14;
        })
      )
      .onNodeClick((node: any) => {
        if (!node) return;
        setHoverNode(null);
        if (node.type === "concept") {
          if (viewModeRef.current === "all") {
            if (selectingForRecommendationRef.current) {
              handleToggleConceptInRecommendation(node.id);
            } else {
              handleConceptClick(node);
              setShowConceptActions(true);
              setShowResearchPanel(false);
            }
          }
        } else if (node.type === "paper") {
          handlePaperClick(node);
        }
      })
      .onNodeHover((node: any) => {
        setHoverNode(node);
        if (containerRef.current) {
          containerRef.current.style.cursor = node ? "pointer" : "default";
        }
      })
      .cooldownTicks(100)
      .onEngineStop(() => graph.zoomToFit(400, 100));

    graphRef.current = graph;

    return () => {
      graphRef.current?._destructor();
      graphRef.current = null;
    };
  }, [handleConceptClick, handlePaperClick, handleToggleConceptInRecommendation]);

  useEffect(() => {
    if (!graphRef.current) return;
    graphRef.current.graphData({ nodes: graphNodes, links: graphLinks });
    graphRef.current.d3ReheatSimulation();
    graphRef.current.refresh();
  }, [graphNodes, graphLinks]);

  useEffect(() => {
    if (!graphRef.current) return;
    graphRef.current.d3Force(
      "charge",
      forceManyBody().strength((node: any) => {
        if (node.type === "paper") return -forceStrength * 0.3;
        if (node.type === "center") return -forceStrength * 1.5;
        const depthBonus = -(node.depth || 0) * 20;
        return -forceStrength * 0.6 + depthBonus;
      })
    );
    graphRef.current.d3ReheatSimulation();
  }, [forceStrength]);

  // Wrap handleDiscoverResearchPoints to also manage UI state
  const onDiscoverResearchPoints = useCallback(async () => {
    setShowConceptActions(false);
    setShowResearchPanel(true);
    await handleDiscoverResearchPoints();
  }, [handleDiscoverResearchPoints]);

  // Wrap handleBack to also manage UI state
  const onBack = useCallback(() => {
    handleBack();
    setShowResearchPanel(false);
    setShowConceptActions(false);
  }, [handleBack]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-gradient-warm">
        <div className="loading-academic">
          Mapping your knowledge landscape...
        </div>
      </div>
    );
  }

  return (
    <div className="h-full relative bg-gradient-warm">
      {/* Graph Canvas */}
      <div ref={containerRef} className="w-full h-full" />

      {/* Top Bar */}
      <div className="absolute top-4 left-4 z-10">
        {viewMode === "concept" && (
          <button
            onClick={onBack}
            className="btn-secondary flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            {t.concepts.backToAll}
          </button>
        )}
      </div>

      {/* Action Buttons - Academic Style */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        {/* Filter Button */}
        <button
          onClick={() => {
            setFilterPanelOpen(!filterPanelOpen);
            if (!filterPanelOpen) {
              setShowFolderMenu(false);
              setShowExportMenu(false);
            }
          }}
          className={`btn-secondary flex items-center gap-2 ${filterPanelOpen ? "border-sepia text-sepia" : ""}`}
        >
          <Search className="w-4 h-4" />
          {t.concepts.filter}
        </button>

        {/* Folder Selector */}
        <div className="relative">
          <button
            onClick={() => {
              setShowFolderMenu(!showFolderMenu);
              if (!showFolderMenu) {
                setFilterPanelOpen(false);
                setShowExportMenu(false);
              }
            }}
            className="btn-secondary flex items-center gap-2"
          >
            <Folder className="w-4 h-4" />
            {activeFolder
              ? folders.find((f) => f.id === activeFolder)?.name || t.common.all
              : t.common.all}
            <ChevronDown className="w-4 h-4" />
          </button>
          {showFolderMenu && (
            <div className="absolute right-0 mt-2 w-48 card-academic overflow-hidden z-20 animate-slide-down">
              <button
                onClick={() => {
                  setActiveFolder("");
                  setShowFolderMenu(false);
                }}
                className={`w-full text-left px-4 py-3 font-body text-sm hover:bg-paper flex items-center gap-2 transition-colors ${activeFolder === "" ? "bg-vellum text-sepia" : "text-muted"}`}
              >
                <Folder className="w-4 w-4" />
                {t.common.all}
              </button>
              {folders.map((folder) => (
                <button
                  key={folder.id}
                  onClick={() => {
                    setActiveFolder(folder.id);
                    setShowFolderMenu(false);
                  }}
                  className={`w-full text-left px-4 py-3 font-body text-sm hover:bg-paper flex items-center gap-2 transition-colors ${activeFolder === folder.id ? "bg-vellum text-sepia" : "text-muted"}`}
                >
                  <Folder className="w-4 h-4" />
                  {folder.name}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Export Dropdown */}
        {viewMode === "all" && (
          <div className="relative">
            <button
              onClick={() => {
                setShowExportMenu(!showExportMenu);
                if (!showExportMenu) {
                  setFilterPanelOpen(false);
                  setShowFolderMenu(false);
                }
              }}
              className="btn-secondary flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              {t.concepts.export}
              <ChevronDown className="w-4 h-4" />
            </button>
            {showExportMenu && (
              <div className="absolute right-0 mt-2 w-56 card-academic overflow-hidden z-20 animate-slide-down">
                <button
                  onClick={() => {
                    handleExportHtml();
                    setShowExportMenu(false);
                  }}
                  className="w-full px-4 py-3 text-left hover:bg-paper flex items-center gap-3 transition-colors"
                >
                  <span className="text-lg">🌐</span>
                  <div>
                    <div className="font-body font-medium text-sepia">
                      {t.export.html}
                    </div>
                    <div className="font-mono text-xs text-faint">
                      {t.export.htmlDesc}
                    </div>
                  </div>
                </button>
                <button
                  onClick={() => {
                    handleExportCanvas();
                    setShowExportMenu(false);
                  }}
                  className="w-full px-4 py-3 text-left hover:bg-paper flex items-center gap-3 transition-colors"
                >
                  <span className="text-lg">🎨</span>
                  <div>
                    <div className="font-body font-medium text-sepia">
                      {t.export.canvas}
                    </div>
                    <div className="font-mono text-xs text-faint">
                      {t.export.canvasDesc}
                    </div>
                  </div>
                </button>
                <button
                  onClick={() => {
                    handleExportMarkdown();
                    setShowExportMenu(false);
                  }}
                  className="w-full px-4 py-3 text-left hover:bg-paper flex items-center gap-3 transition-colors"
                >
                  <span className="text-lg">📝</span>
                  <div>
                    <div className="font-body font-medium text-sepia">
                      {t.export.markdown}
                    </div>
                    <div className="font-mono text-xs text-faint">
                      {t.export.markdownDesc}
                    </div>
                  </div>
                </button>
              </div>
            )}
          </div>
        )}

        {viewMode === "all" && (
          <button
            onClick={() => setDedupOpen(true)}
            className="btn-primary flex items-center gap-2"
          >
            🔄 {t.concepts.dedupScan}
          </button>
        )}
      </div>

      {/* Info Panel - Academic Style */}
      <div className="absolute bottom-16 left-4 card-academic p-4 z-10">
        <div className="font-mono text-xs text-muted uppercase tracking-wider mb-1">
          {viewMode === "all"
            ? t.concepts.knowledgeGraph
            : t.concepts.conceptDetails}
        </div>
        <div className="font-display text-lg text-sepia font-medium">
          {viewMode === "all"
            ? `${concepts.length} ${t.concepts.concepts}`
            : selectedConcept?.text}
        </div>
        <div className="font-body text-xs text-muted mt-1">
          {viewMode === "all"
            ? t.concepts.clickToView
            : t.concepts.clickPaperToView}
        </div>

        {/* Force Strength Slider */}
        <div className="mt-3 pt-3 border-t border-academic">
          <div className="flex items-center justify-between mb-1">
            <span className="font-mono text-xs text-muted">
              {t.concepts.nodeRepulsion}
            </span>
            <span className="font-mono text-xs text-sepia font-medium">
              {forceStrength}
            </span>
          </div>
          <input
            type="range"
            min="50"
            max="400"
            value={forceStrength}
            onChange={(e) => setForceStrength(Number(e.target.value))}
            className="w-full h-1.5 bg-paper rounded-lg appearance-none cursor-pointer accent-sepia"
          />
          <div className="flex justify-between font-mono text-[10px] text-faint mt-1">
            <span>{t.concepts.compact}</span>
            <span>{t.concepts.spread}</span>
          </div>
        </div>
      </div>

      {/* Concept Action Panel - Redesigned */}
      {showConceptActions && selectedConcept && (
        <div
          className="absolute top-4 right-4 z-20 w-80 animate-slide-down"
          style={{
            background:
              "linear-gradient(135deg, rgba(250, 248, 245, 0.98) 0%, rgba(245, 240, 232, 0.98) 100%)",
            border: "1px solid rgba(184, 134, 11, 0.12)",
            borderRadius: "16px",
            boxShadow:
              "0 8px 32px rgba(44, 24, 16, 0.08), 0 2px 8px rgba(44, 24, 16, 0.04)",
            overflow: "hidden",
          }}
        >
          {/* Header with decorative accent */}
          <div
            className="px-5 py-4"
            style={{
              borderBottom: "1px solid rgba(184, 134, 11, 0.08)",
              background:
                "linear-gradient(180deg, rgba(184, 134, 11, 0.03) 0%, transparent 100%)",
            }}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 pr-3">
                <h3
                  className="font-display text-lg leading-tight"
                  style={{ color: "var(--color-sepia)", fontWeight: 500 }}
                >
                  {selectedConcept.text}
                </h3>
                <div className="flex items-center gap-3 mt-2">
                  {selectedConcept.category && (
                    <span
                      className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-mono"
                      style={{
                        backgroundColor:
                          CATEGORY_COLORS[selectedConcept.category] + "12",
                        color: CATEGORY_COLORS[selectedConcept.category],
                        border: `1px solid ${CATEGORY_COLORS[selectedConcept.category]}25`,
                      }}
                    >
                      {selectedConcept.category}
                    </span>
                  )}
                  <span
                    className="font-mono text-xs"
                    style={{ color: "var(--color-muted)" }}
                  >
                    {selectedConcept.paper_count || 0} 篇论文
                  </span>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowConceptActions(false);
                  setSelectedConcept(null);
                }}
                className="w-8 h-8 rounded-full flex items-center justify-center transition-all"
                style={{
                  color: "var(--color-muted)",
                  background: "transparent",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(184, 134, 11, 0.08)";
                  e.currentTarget.style.color = "var(--color-sepia)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "var(--color-muted)";
                }}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Action buttons - cleaner design */}
          <div className="p-4 space-y-2">
            <button
              onClick={onDiscoverResearchPoints}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all"
              style={{
                background:
                  "linear-gradient(135deg, var(--color-sepia) 0%, var(--color-copper) 100%)",
                color: "var(--color-vellum)",
                fontFamily: "var(--font-body)",
                fontWeight: 500,
                fontSize: "0.875rem",
              }}
            >
              <span className="text-lg">🔍</span>
              <span>发现研究点</span>
            </button>
            <button
              onClick={handleStartRecommendationSelection}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all"
              style={{
                background: "var(--color-paper)",
                color: "var(--color-sepia)",
                border: "1px solid rgba(184, 134, 11, 0.15)",
                fontFamily: "var(--font-body)",
                fontWeight: 500,
                fontSize: "0.875rem",
              }}
            >
              <span className="text-lg">📚</span>
              <span>推荐相关论文</span>
            </button>
            {selectedConcept.papers && selectedConcept.papers.length > 0 && (
              <button
                onClick={handleViewPapers}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all"
                style={{
                  background: "var(--color-paper)",
                  color: "var(--color-sepia)",
                  border: "1px solid rgba(184, 134, 11, 0.15)",
                  fontFamily: "var(--font-body)",
                  fontWeight: 500,
                  fontSize: "0.875rem",
                }}
              >
                <span className="text-lg">📄</span>
                <span>查看关联论文</span>
                <span
                  className="ml-auto px-2 py-0.5 rounded-full text-xs font-mono"
                  style={{
                    background: "rgba(184, 134, 11, 0.1)",
                    color: "var(--color-sepia)",
                  }}
                >
                  {selectedConcept.papers.length}
                </span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Hover Tooltip */}
      {hoverNode && !showConceptActions && (
        <div className="absolute top-4 right-4 card-academic p-3 z-10 max-w-xs pointer-events-none animate-slide-down">
          <div className="font-display text-sepia text-sm">
            {hoverNode.name}
          </div>
          <div className="flex items-center gap-2 mt-1">
            {hoverNode.type === "paper" ? (
              <span
                className="badge-academic"
                style={{
                  backgroundColor: "#4a6b8a15",
                  color: "#4a6b8a",
                  borderColor: "#4a6b8a30",
                }}
              >
                {t.concepts.paperNode}
              </span>
            ) : hoverNode.type === "center" ? (
              <span
                className="badge-academic"
                style={{
                  backgroundColor: "#d4a01215",
                  color: "#d4a012",
                  borderColor: "#d4a01230",
                }}
              >
                {t.concepts.centerConcept}
              </span>
            ) : (
              <>
                <span
                  className="badge-academic"
                  style={{
                    backgroundColor:
                      CATEGORY_COLORS[hoverNode.category || "method"] + "15",
                    color: CATEGORY_COLORS[hoverNode.category || "method"],
                    borderColor:
                      CATEGORY_COLORS[hoverNode.category || "method"] + "30",
                  }}
                >
                  {hoverNode.category}
                </span>
                <span className="font-mono text-xs text-muted">
                  L{hoverNode.depth}
                </span>
              </>
            )}
          </div>
          {hoverNode.type === "concept" && (
            <div className="font-body text-xs text-faint mt-1">
              {t.concepts.clickToView}
            </div>
          )}
          {hoverNode.type === "paper" && (
            <div className="font-body text-xs text-faint mt-1">
              {t.concepts.clickPaperToView}
            </div>
          )}
        </div>
      )}

      {/* Paper Detail Panel - Redesigned */}
      {selectedPaper && (
        <div
          className="absolute bottom-20 right-4 z-20 max-h-[75vh] overflow-hidden animate-slide-up"
          style={{
            width: "420px",
            background:
              "linear-gradient(135deg, rgba(250, 248, 245, 0.98) 0%, rgba(245, 240, 232, 0.98) 100%)",
            border: "1px solid rgba(184, 134, 11, 0.12)",
            borderRadius: "16px",
            boxShadow:
              "0 12px 48px rgba(44, 24, 16, 0.1), 0 4px 16px rgba(44, 24, 16, 0.05)",
          }}
        >
          {/* Header */}
          <div
            className="px-5 py-4 sticky top-0"
            style={{
              borderBottom: "1px solid rgba(184, 134, 11, 0.08)",
              background:
                "linear-gradient(180deg, rgba(184, 134, 11, 0.04) 0%, transparent 100%)",
            }}
          >
            <div className="flex items-start justify-between">
              <h3
                className="font-display text-base leading-snug pr-3"
                style={{ color: "var(--color-sepia)", fontWeight: 500 }}
              >
                {selectedPaper.title}
              </h3>
              <button
                onClick={() => setSelectedPaper(null)}
                className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-all"
                style={{ color: "var(--color-muted)" }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(184, 134, 11, 0.08)";
                  e.currentTarget.style.color = "var(--color-sepia)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "var(--color-muted)";
                }}
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Quick stats row */}
            <div className="flex items-center gap-4 mt-3">
              {selectedPaper.year && (
                <div className="flex items-center gap-1.5">
                  <span className="text-sm">📅</span>
                  <span
                    className="font-mono text-xs"
                    style={{ color: "var(--color-muted)" }}
                  >
                    {selectedPaper.year}
                  </span>
                </div>
              )}
              {selectedPaper.citation_count !== undefined && (
                <div className="flex items-center gap-1.5">
                  <span className="text-sm">📊</span>
                  <span
                    className="font-mono text-xs"
                    style={{ color: "var(--color-muted)" }}
                  >
                    {selectedPaper.citation_count} 引用
                  </span>
                </div>
              )}
              {selectedPaper.venue && (
                <div className="flex items-center gap-1.5">
                  <span className="text-sm">📖</span>
                  <span
                    className="font-body text-xs truncate max-w-[120px]"
                    style={{ color: "var(--color-muted)" }}
                  >
                    {selectedPaper.venue}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Scrollable content */}
          <div className="overflow-y-auto max-h-[calc(75vh-100px)] p-5 space-y-5">
            {/* TLDR - Highlighted */}
            {selectedPaper.tldr && (
              <div
                className="p-4 rounded-xl"
                style={{
                  background:
                    "linear-gradient(135deg, rgba(45, 90, 39, 0.06) 0%, rgba(45, 90, 39, 0.02) 100%)",
                  border: "1px solid rgba(45, 90, 39, 0.1)",
                }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm">💡</span>
                  <span
                    className="font-mono text-xs uppercase tracking-wider"
                    style={{ color: "#2d5a27" }}
                  >
                    TL;DR
                  </span>
                </div>
                <div
                  className="font-quote text-sm leading-relaxed"
                  style={{ color: "#2d5a27" }}
                >
                  {selectedPaper.tldr}
                </div>
              </div>
            )}

            {/* Authors */}
            {selectedPaper.authors && selectedPaper.authors.length > 0 && (
              <div>
                <div
                  className="font-mono text-xs uppercase tracking-wider mb-2"
                  style={{ color: "var(--color-muted)" }}
                >
                  作者
                </div>
                <div
                  className="font-body text-sm leading-relaxed"
                  style={{ color: "var(--color-sepia)" }}
                >
                  {selectedPaper.authors.slice(0, 4).join(", ")}
                  {selectedPaper.authors.length > 4 && (
                    <span style={{ color: "var(--color-muted)" }}>
                      {" "}
                      +{selectedPaper.authors.length - 4} 位
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Keywords - pill design */}
            {selectedPaper.keywords && selectedPaper.keywords.length > 0 && (
              <div>
                <div
                  className="font-mono text-xs uppercase tracking-wider mb-2"
                  style={{ color: "var(--color-muted)" }}
                >
                  关键词
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {selectedPaper.keywords.slice(0, 8).map((kw, i) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 rounded-full text-xs font-mono"
                      style={{
                        backgroundColor: "rgba(184, 134, 11, 0.06)",
                        color: "var(--color-sepia)",
                        border: "1px solid rgba(184, 134, 11, 0.1)",
                      }}
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Abstract */}
            {selectedPaper.abstract && (
              <div>
                <div
                  className="font-mono text-xs uppercase tracking-wider mb-2"
                  style={{ color: "var(--color-muted)" }}
                >
                  摘要
                </div>
                <div
                  className="font-body text-sm leading-relaxed"
                  style={{ color: "var(--color-ink)" }}
                >
                  {selectedPaper.abstract}
                </div>
              </div>
            )}

            {/* Contributions */}
            {selectedPaper.contributions &&
              selectedPaper.contributions.length > 0 && (
                <div>
                  <div
                    className="font-mono text-xs uppercase tracking-wider mb-3"
                    style={{ color: "var(--color-muted)" }}
                  >
                    核心贡献
                  </div>
                  <div className="space-y-2">
                    {selectedPaper.contributions.slice(0, 3).map((c, i) => (
                      <div key={i} className="flex items-start gap-3">
                        <span
                          className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-mono flex-shrink-0 mt-0.5"
                          style={{
                            background:
                              "linear-gradient(135deg, var(--color-sepia) 0%, var(--color-copper) 100%)",
                            color: "var(--color-vellum)",
                          }}
                        >
                          {i + 1}
                        </span>
                        <span
                          className="font-body text-sm leading-relaxed"
                          style={{ color: "var(--color-ink)" }}
                        >
                          {c}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            {/* DOI Link */}
            <div
              className="pt-4"
              style={{ borderTop: "1px solid rgba(184, 134, 11, 0.08)" }}
            >
              <div
                className="font-mono text-xs uppercase tracking-wider mb-2"
                style={{ color: "var(--color-muted)" }}
              >
                DOI
              </div>
              {selectedPaper.s2_doi ? (
                <a
                  href={`https://doi.org/${selectedPaper.s2_doi}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-xs break-all transition-colors"
                  style={{ color: "#4a6b8a" }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.color = "var(--color-sepia)")
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.color = "#4a6b8a")
                  }
                >
                  {selectedPaper.s2_doi} →
                </a>
              ) : (
                <div
                  className="font-mono text-xs break-all"
                  style={{ color: "var(--color-muted)" }}
                >
                  {selectedPaper.doi}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Research Points Panel - Redesigned */}
      {showResearchPanel && (
        <div
          className="absolute top-20 left-4 z-20 max-h-[80vh] overflow-hidden animate-slide-up"
          style={{
            width: "520px",
            background:
              "linear-gradient(135deg, rgba(250, 248, 245, 0.98) 0%, rgba(245, 240, 232, 0.98) 100%)",
            border: "1px solid rgba(184, 134, 11, 0.12)",
            borderRadius: "16px",
            boxShadow:
              "0 12px 48px rgba(44, 24, 16, 0.1), 0 4px 16px rgba(44, 24, 16, 0.05)",
          }}
        >
          {/* Header */}
          <div
            className="px-5 py-4 sticky top-0"
            style={{
              borderBottom: "1px solid rgba(184, 134, 11, 0.08)",
              background:
                "linear-gradient(180deg, rgba(184, 134, 11, 0.04) 0%, transparent 100%)",
            }}
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-lg">🔍</span>
                  <h3
                    className="font-display text-base"
                    style={{ color: "var(--color-sepia)", fontWeight: 500 }}
                  >
                    研究点发现
                  </h3>
                </div>
                <p
                  className="font-body text-xs mt-1.5"
                  style={{ color: "var(--color-muted)" }}
                >
                  基于「{researchPoints?.concept_name || selectedConcept?.text}
                  」的图谱分析
                </p>
              </div>
              <button
                onClick={() => setShowResearchPanel(false)}
                className="w-8 h-8 rounded-full flex items-center justify-center transition-all"
                style={{ color: "var(--color-muted)" }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(184, 134, 11, 0.08)";
                  e.currentTarget.style.color = "var(--color-sepia)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "var(--color-muted)";
                }}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Scrollable content */}
          <div className="overflow-y-auto max-h-[calc(80vh-90px)] p-5 space-y-5">
            {loadingResearchPoints ? (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <div
                    className="loading-academic"
                    style={{ minHeight: "100px" }}
                  >
                    正在分析图谱结构...
                  </div>
                  <p
                    className="font-body text-xs mt-2"
                    style={{ color: "var(--color-muted)" }}
                  >
                    遍历祖先节点、后代节点和边缘节点
                  </p>
                </div>
              </div>
            ) : researchPoints ? (
              <>
                {/* Analysis Context - Compact Stats */}
                <div
                  className="flex items-center gap-4 px-4 py-3 rounded-xl"
                  style={{
                    background: "rgba(184, 134, 11, 0.04)",
                    border: "1px solid rgba(184, 134, 11, 0.08)",
                  }}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm">⬆️</span>
                    <div>
                      <div
                        className="font-display text-base"
                        style={{ color: "var(--color-sepia)" }}
                      >
                        {researchPoints.analysis_context.ancestors.length}
                      </div>
                      <div
                        className="font-mono text-[10px]"
                        style={{ color: "var(--color-muted)" }}
                      >
                        祖先
                      </div>
                    </div>
                  </div>
                  <div
                    className="w-px h-8"
                    style={{ background: "rgba(184, 134, 11, 0.1)" }}
                  />
                  <div className="flex items-center gap-2">
                    <span className="text-sm">⬇️</span>
                    <div>
                      <div
                        className="font-display text-base"
                        style={{ color: "var(--color-sepia)" }}
                      >
                        {researchPoints.analysis_context.descendants.length}
                      </div>
                      <div
                        className="font-mono text-[10px]"
                        style={{ color: "var(--color-muted)" }}
                      >
                        后代
                      </div>
                    </div>
                  </div>
                  <div
                    className="w-px h-8"
                    style={{ background: "rgba(184, 134, 11, 0.1)" }}
                  />
                  <div className="flex items-center gap-2">
                    <span className="text-sm">🍃</span>
                    <div>
                      <div
                        className="font-display text-base"
                        style={{ color: "var(--color-sepia)" }}
                      >
                        {researchPoints.analysis_context.edge_nodes.length}
                      </div>
                      <div
                        className="font-mono text-[10px]"
                        style={{ color: "var(--color-muted)" }}
                      >
                        边缘
                      </div>
                    </div>
                  </div>
                </div>

                {/* Research Points Cards */}
                <div className="space-y-4">
                  {researchPoints.research_points.map((point, i) => (
                    <div
                      key={i}
                      className="group rounded-xl overflow-hidden transition-all"
                      style={{
                        border: "1px solid rgba(184, 134, 11, 0.1)",
                        background: "transparent",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor =
                          "rgba(184, 134, 11, 0.2)";
                        e.currentTarget.style.background =
                          "rgba(184, 134, 11, 0.02)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor =
                          "rgba(184, 134, 11, 0.1)";
                        e.currentTarget.style.background = "transparent";
                      }}
                    >
                      {/* Card Header */}
                      <div className="px-4 py-3 flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3 flex-1">
                          <span
                            className="w-6 h-6 rounded-lg flex items-center justify-center text-xs font-mono flex-shrink-0 mt-0.5"
                            style={{
                              background:
                                "linear-gradient(135deg, var(--color-sepia) 0%, var(--color-copper) 100%)",
                              color: "var(--color-vellum)",
                            }}
                          >
                            {i + 1}
                          </span>
                          <div>
                            <h4
                              className="font-display text-sm leading-snug"
                              style={{
                                color: "var(--color-sepia)",
                                fontWeight: 500,
                              }}
                            >
                              {point.title}
                            </h4>
                            {point.hypothesis && (
                              <p
                                className="font-body text-xs mt-1 italic"
                                style={{ color: "#4a6b8a" }}
                              >
                                {point.hypothesis}
                              </p>
                            )}
                          </div>
                        </div>
                        {/* Compact tags */}
                        <div className="flex gap-1.5 flex-shrink-0 flex-wrap">
                          <span
                            className="px-1.5 py-0.5 rounded text-xs font-medium"
                            style={{
                              backgroundColor:
                                point.difficulty === "low"
                                  ? "rgba(45, 90, 39, 0.12)"
                                  : point.difficulty === "medium"
                                    ? "rgba(184, 134, 11, 0.12)"
                                    : "rgba(163, 51, 59, 0.12)",
                              color:
                                point.difficulty === "low"
                                  ? "#2d5a27"
                                  : point.difficulty === "medium"
                                    ? "#b8860b"
                                    : "#a33b3b",
                            }}
                          >
                            {point.difficulty === "low" ? "低难度" : point.difficulty === "medium" ? "中难度" : "高难度"}
                          </span>
                          <span
                            className="px-1.5 py-0.5 rounded text-xs font-medium"
                            style={{
                              backgroundColor:
                                point.novelty === "high"
                                  ? "rgba(194, 65, 12, 0.12)"
                                  : point.novelty === "moderate"
                                    ? "rgba(74, 107, 138, 0.12)"
                                    : "rgba(168, 154, 138, 0.12)",
                              color:
                                point.novelty === "high"
                                  ? "#c2410c"
                                  : point.novelty === "moderate"
                                    ? "#4a6b8a"
                                    : "#a89a8a",
                            }}
                          >
                            {point.novelty === "high" ? "高创新" : point.novelty === "moderate" ? "中创新" : "低创新"}
                          </span>
                          <span
                            className="px-1.5 py-0.5 rounded text-xs font-medium"
                            style={{
                              backgroundColor:
                                point.potential_impact === "transformative"
                                  ? "rgba(212, 160, 18, 0.12)"
                                  : point.potential_impact === "broad"
                                    ? "rgba(74, 107, 138, 0.12)"
                                    : "rgba(168, 154, 138, 0.12)",
                              color:
                                point.potential_impact === "transformative"
                                  ? "#d4a012"
                                  : point.potential_impact === "broad"
                                    ? "#4a6b8a"
                                    : "#a89a8a",
                            }}
                          >
                            {point.potential_impact === "transformative" ? "变革性" : point.potential_impact === "broad" ? "广泛" : "小众"}
                          </span>
                        </div>
                      </div>

                      {/* Card Body */}
                      <div className="px-4 pb-4 pl-13">
                        <p
                          className="font-body text-sm leading-relaxed"
                          style={{ color: "var(--color-ink)" }}
                        >
                          {point.description}
                        </p>

                        {/* Method & Rationale */}
                        <div
                          className="mt-3 px-3 py-2 rounded-lg text-xs"
                          style={{ background: "rgba(184, 134, 11, 0.04)" }}
                        >
                          <span style={{ color: "var(--color-muted)" }}>
                            {(t.concepts.researchPoints.method as Record<string, string>)[point.discovery_method] || point.discovery_method}
                          </span>
                          <span
                            className="mx-2"
                            style={{ color: "rgba(184, 134, 11, 0.2)" }}
                          >
                            ·
                          </span>
                          <span style={{ color: "var(--color-sepia)" }}>
                            {point.rationale}
                          </span>
                        </div>

                        {/* Related Concepts */}
                        {point.related_concepts &&
                          point.related_concepts.length > 0 && (
                            <div className="mt-3 flex flex-wrap gap-1.5">
                              {point.related_concepts
                                .slice(0, 4)
                                .map((c, j) => (
                                  <span
                                    key={j}
                                    className="px-2 py-0.5 rounded-full text-xs font-mono"
                                    style={{
                                      backgroundColor:
                                        "rgba(184, 134, 11, 0.06)",
                                      color: "var(--color-sepia)",
                                    }}
                                  >
                                    {c}
                                  </span>
                                ))}
                            </div>
                          )}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}

      {/* Legend - Academic Style */}
      <div className="absolute bottom-16 right-4 card-academic p-4 z-10">
        <div className="font-mono text-xs text-sepia uppercase tracking-wider mb-2">
          {t.concepts.legend}
        </div>
        <div className="space-y-1.5">
          {/* Concept Categories - Hierarchy */}
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: CATEGORY_COLORS.field }}
            />
            <span className="font-body text-xs text-muted">
              {t.concepts.category.field}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: CATEGORY_COLORS.direction }}
            />
            <span className="font-body text-xs text-muted">
              {t.concepts.category.direction}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: CATEGORY_COLORS.subdirection }}
            />
            <span className="font-body text-xs text-muted">
              {t.concepts.category.subdirection}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: CATEGORY_COLORS.task }}
            />
            <span className="font-body text-xs text-muted">
              {t.concepts.category.task}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: CATEGORY_COLORS.method }}
            />
            <span className="font-body text-xs text-muted">
              {t.concepts.category.method}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: CATEGORY_COLORS.technique }}
            />
            <span className="font-body text-xs text-muted">
              {t.concepts.category.technique}
            </span>
          </div>
          {/* Divider */}
          <div className="border-t border-academic my-1" />
          {/* Contribution Types */}
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: CATEGORY_COLORS.dataset }}
            />
            <span className="font-body text-xs text-muted">
              {t.concepts.category.dataset}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: CATEGORY_COLORS.finding }}
            />
            <span className="font-body text-xs text-muted">
              {t.concepts.category.finding}
            </span>
          </div>
          {/* Divider */}
          <div className="border-t border-academic my-1" />
          {/* Special Nodes */}
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: PAPER_COLOR }}
            />
            <span className="font-body text-xs text-muted">
              {t.concepts.paperNode}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: CENTER_COLOR }}
            />
            <span className="font-body text-xs text-muted">
              {t.concepts.centerConcept}
            </span>
          </div>
        </div>
      </div>

      {/* Dedup Panel */}
      {dedupOpen && (
        <DedupPanel isOpen={dedupOpen} onClose={() => setDedupOpen(false)} />
      )}

      {/* Filter Panel */}
      {filterPanelOpen && (
        <FilterPanel
          searchQuery={searchQuery}
          selectedCategories={selectedCategories}
          graphNodes={graphNodes}
          onSearch={handleSearch}
          onCategoryChange={handleCategoryChange}
          onFocusNode={handleFocusNode}
          onClose={() => setFilterPanelOpen(false)}
        />
      )}

      {/* Selection Mode Banner */}
      {isSelectingForRecommendation && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 card-academic px-4 py-2 animate-slide-down">
          <div className="flex items-center gap-3">
            <span className="font-body text-sm text-sepia">
              {t.concepts.recommendation.selectedConcepts}:{" "}
              {selectedConceptsForRecommendation.length}
            </span>
            <button
              onClick={() => setIsSelectingForRecommendation(false)}
              className="btn-secondary-xs"
            >
              {t.common.confirm}
            </button>
            <button
              onClick={() => {
                setIsSelectingForRecommendation(false);
                setSelectedConceptsForRecommendation([]);
                setRecommendationPanelOpen(false);
              }}
              className="btn-secondary-xs text-status-error border-status-error"
            >
              {t.common.cancel}
            </button>
          </div>
        </div>
      )}

      {/* Recommendation Panel */}
      <RecommendationPanel
        isOpen={recommendationPanelOpen}
        onClose={() => {
          setRecommendationPanelOpen(false);
          setIsSelectingForRecommendation(false);
          setSelectedConceptsForRecommendation([]);
        }}
        selectedConcepts={selectedConceptsForRecommendation}
        onAddConcept={handleAddConceptToRecommendation}
        onRemoveConcept={handleRemoveConceptFromRecommendation}
        concepts={concepts}
      />
    </div>
  );
}
