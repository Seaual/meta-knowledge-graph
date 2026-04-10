// frontend/src/components/ConceptGraphInChat.tsx
// 聊天中嵌入的概念图谱组件 - 与概念页面完全一致
// 不包含右上角功能按钮和节点点击功能面板

import { useEffect, useRef, useState } from "react";
import ForceGraph from "force-graph";
import { forceManyBody, forceCollide, forceLink, forceCenter } from "d3-force";
import { graphApi, foldersApi } from "../lib/api";
import { Folder, ChevronDown } from "lucide-react";

// Types
interface Concept {
  id: string;
  text: string;
  text_en?: string;
  category: string | null | undefined;
  paper_count: number;
}

interface GraphNode {
  id: string;
  name: string;
  name_en?: string;
  type: "concept";
  category?: string;
  paperCount?: number;
  depth?: number;
  x?: number;
  y?: number;
}

interface Folder {
  id: string;
  name: string;
}

// Category colors - 与概念页面完全一致
const CATEGORY_COLORS: Record<string, string> = {
  field: "#6b4423", // sepia
  direction: "#b8860b", // amber
  subdirection: "#9a6b3c", // copper
  task: "#4a6b8a", // slate blue
  method: "#c2410c", // terracotta
  technique: "#2d5a27", // forest green
  dataset: "#5c4d7d", // purple
  finding: "#d4a012", // gold
};

// Category sizes - 与概念页面完全一致
const CATEGORY_SIZES: Record<string, number> = {
  field: 16,
  direction: 14,
  subdirection: 12,
  dataset: 12,
  finding: 12,
  task: 10,
  method: 8,
  technique: 6,
};

// Category collision radii - 与概念页面完全一致
const CATEGORY_RADII: Record<string, number> = {
  field: 20,
  direction: 18,
  subdirection: 16,
  dataset: 16,
  finding: 16,
  task: 14,
  method: 12,
  technique: 10,
};

interface Props {
  // 可选：直接传入数据（兼容旧接口）
  data?: {
    id: string;
    name: string;
    category?: string;
    paper_count: number;
    children?: Array<{
      id: string;
      name: string;
      paper_count?: number;
      category?: string;
    }>;
    parents?: Array<{
      id: string;
      name: string;
      paper_count?: number;
      category?: string;
    }>;
  };
  onNodeClick?: (node: {
    id: string;
    name: string;
    category?: string;
    paper_count: number;
  }) => void;
}

export default function ConceptGraphInChat({
  data: _data,
  onNodeClick,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const [error, setError] = useState<string | null>(null);

  // 文件夹相关状态
  const [folders, setFolders] = useState<Folder[]>([]);
  const [activeFolder, setActiveFolder] = useState<string>("");
  const [showFolderMenu, setShowFolderMenu] = useState(false);
  const [loading, setLoading] = useState(true);

  // 图谱数据
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [edges, setEdges] = useState<{ source: string; target: string }[]>([]);
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [graphLinks, setGraphLinks] = useState<
    { source: string; target: string }[]
  >([]);

  // 加载文件夹列表
  useEffect(() => {
    foldersApi
      .list()
      .then((res) => {
        setFolders(res.data);
        // 如果只有一个文件夹或没有文件夹，自动选择
        if (res.data.length <= 1) {
          setActiveFolder(res.data[0]?.id || "");
        }
      })
      .catch((err) => {
        console.error("Failed to load folders:", err);
      });
  }, []);

  // 加载图谱数据
  useEffect(() => {
    // 如果有多个文件夹且未选择，不加载
    if (folders.length > 1 && !activeFolder) {
      setLoading(false);
      return;
    }

    const loadData = async () => {
      setLoading(true);
      try {
        const graphRes = await graphApi.data(activeFolder || undefined);
        const nodesFromGraph = graphRes.data.nodes.map((n: any) => ({
          id: n.id,
          text: n.label,
          text_en: n.label_en,
          category: n.category,
          paper_count: n.paper_count || 0,
        }));
        setConcepts(nodesFromGraph);
        setEdges(graphRes.data.edges);
        setError(null);
      } catch (err) {
        console.error("Failed to load graph:", err);
        setError("加载图谱失败");
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [activeFolder, folders.length]);

  // 构建图谱节点和边
  useEffect(() => {
    if (concepts.length === 0) return;

    // 计算节点深度
    const parentMap = new Map<string, string>();
    edges.forEach((e) => parentMap.set(e.target, e.source));

    const getNodeDepth = (nodeId: string): number => {
      let depth = 0;
      let current = nodeId;
      const visited = new Set<string>();
      while (parentMap.has(current) && !visited.has(current)) {
        visited.add(current);
        current = parentMap.get(current)!;
        depth++;
      }
      return depth;
    };

    const nodes: GraphNode[] = concepts.map((c) => ({
      id: c.id,
      name: c.text,
      name_en: c.text_en,
      type: "concept",
      category: c.category || "method",
      paperCount: c.paper_count,
      depth: getNodeDepth(c.id),
    }));

    const links = edges.map((e) => ({
      source: e.source,
      target: e.target,
    }));

    setGraphNodes(nodes);
    setGraphLinks(links);
  }, [concepts, edges]);

  // 初始化图谱 - 与概念页面完全一致
  useEffect(() => {
    if (!containerRef.current || graphNodes.length === 0) return;

    if (graphRef.current) {
      graphRef.current._destructor();
    }

    const graph = new ForceGraph(containerRef.current!)
      .graphData({ nodes: graphNodes, links: graphLinks })
      .nodeId("id")
      .nodeLabel((node: any) => node.name)
      .nodeVal((node: any) => {
        return 1 + Math.sqrt(node.paperCount || 0) * 0.3;
      })
      .nodeCanvasObject(
        (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          // 与概念页面完全一致的渲染逻辑
          const baseSize = CATEGORY_SIZES[node.category || "method"] || 10;
          const size = baseSize + Math.sqrt(node.paperCount || 0) * 0.3;
          const color = CATEGORY_COLORS[node.category || "method"] || "#8a7a6a";

          const x = node.x || 0;
          const y = node.y || 0;

          // 绘制节点 - 空心圆形 + 中心小圆点
          ctx.beginPath();
          ctx.arc(x, y, size, 0, 2 * Math.PI);
          ctx.fillStyle = color + "30";
          ctx.fill();
          ctx.strokeStyle = color;
          ctx.lineWidth = 2 / globalScale;
          ctx.stroke();
          ctx.beginPath();
          ctx.arc(x, y, size * 0.3, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();

          // 绘制标签
          if (globalScale > 0.5) {
            const fontSize = 11;
            ctx.font = `${fontSize}px 'Source Sans 3', sans-serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillStyle = "#2c1810";
            const label =
              node.name && node.name.length > 30
                ? node.name.substring(0, 30) + "..."
                : node.name || "";
            ctx.fillText(label, x, y + size + 4);
          }
        }
      )
      .linkColor(() => "#d4c4b0")
      .linkWidth(1)
      .linkDirectionalParticles(2)
      .linkDirectionalParticleWidth(2)
      .linkDirectionalParticleColor(() => "#b8860b")
      .d3AlphaDecay(0.02)
      .d3VelocityDecay(0.3)
      .d3Force(
        "charge",
        forceManyBody().strength((node: any) => {
          const depthBonus = -(node.depth || 0) * 20;
          return -80 + depthBonus;
        })
      )
      .d3Force("center", forceCenter(250, 250))
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
          return CATEGORY_RADII[node.category || "method"] || 14;
        })
      )
      .onNodeClick((node: any) => {
        // 只通知父组件，不显示功能面板
        if (onNodeClick && node) {
          onNodeClick({
            id: node.id,
            name: node.name,
            category: node.category,
            paper_count: node.paperCount || 0,
          });
        }
      })
      .cooldownTicks(100)
      .onEngineStop(() => graph.zoomToFit(400, 100));

    graphRef.current = graph;

    return () => {
      if (graphRef.current) {
        graphRef.current._destructor();
      }
    };
  }, [graphNodes, graphLinks, onNodeClick]);

  // 加载中
  if (loading) {
    return (
      <div className="my-3 p-8 rounded-xl bg-gradient-warm flex items-center justify-center">
        <div className="text-muted text-sm">加载图谱中...</div>
      </div>
    );
  }

  // 错误
  if (error) {
    return (
      <div className="my-3 p-4 rounded-xl bg-red-50 border border-red-200">
        <p className="text-red-600 text-sm">{error}</p>
      </div>
    );
  }

  // 多文件夹选择
  if (folders.length > 1 && !activeFolder) {
    return (
      <div className="my-3 p-6 rounded-xl bg-gradient-warm">
        <div className="text-center mb-4">
          <p className="text-sepia font-medium">请选择要显示的文件夹图谱</p>
        </div>
        <div className="flex flex-wrap justify-center gap-2">
          {folders.map((folder) => (
            <button
              key={folder.id}
              onClick={() => setActiveFolder(folder.id)}
              className="px-4 py-2 rounded-lg bg-paper border border-sepia/20 text-sepia text-sm hover:bg-vellum transition-colors"
            >
              <Folder className="w-4 h-4 inline mr-2" />
              {folder.name}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="concept-graph-in-chat my-3">
      <div
        className="rounded-xl overflow-hidden shadow-lg"
        style={{
          background: "linear-gradient(135deg, #faf8f5 0%, #f5f0e8 100%)",
          border: "1px solid rgba(184, 134, 11, 0.15)",
        }}
      >
        {/* 标题栏 - 与概念页面一致 */}
        <div
          className="px-4 py-2 flex items-center justify-between"
          style={{
            background: "rgba(184, 134, 11, 0.08)",
            borderBottom: "1px solid rgba(184, 134, 11, 0.1)",
          }}
        >
          <span className="text-sm font-medium" style={{ color: "#8b4513" }}>
            📊 概念图谱
          </span>

          {/* 文件夹选择器 */}
          {folders.length > 1 && (
            <div className="relative">
              <button
                onClick={() => setShowFolderMenu(!showFolderMenu)}
                className="flex items-center gap-1.5 text-xs px-2 py-1 rounded hover:bg-amber/10 transition-colors"
                style={{ color: "#666" }}
              >
                <Folder className="w-3.5 h-3.5" />
                {folders.find((f) => f.id === activeFolder)?.name || "全部"}
                <ChevronDown className="w-3.5 h-3.5" />
              </button>

              {showFolderMenu && (
                <div className="absolute right-0 mt-1 w-40 bg-paper rounded-lg shadow-lg border border-sepia/10 z-20">
                  <button
                    onClick={() => {
                      setActiveFolder("");
                      setShowFolderMenu(false);
                    }}
                    className={`w-full text-left px-3 py-2 text-xs hover:bg-vellum transition-colors rounded-t-lg ${!activeFolder ? "text-sepia bg-vellum" : "text-muted"}`}
                  >
                    全部
                  </button>
                  {folders.map((folder) => (
                    <button
                      key={folder.id}
                      onClick={() => {
                        setActiveFolder(folder.id);
                        setShowFolderMenu(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-xs hover:bg-vellum transition-colors ${activeFolder === folder.id ? "text-sepia bg-vellum" : "text-muted"}`}
                    >
                      {folder.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {folders.length <= 1 && (
            <span className="text-xs" style={{ color: "#666" }}>
              {folders.find((f) => f.id === activeFolder)?.name || "全部概念"}
            </span>
          )}
        </div>

        {/* 图谱容器 - 与概念页面完全一致 */}
        <div
          ref={containerRef}
          style={{
            width: "100%",
            height: 500,
            minWidth: 500,
            cursor: "grab",
          }}
        />

        {/* 图例 - 与概念页面一致 */}
        <div
          className="px-4 py-2 flex items-center justify-center gap-4 text-xs overflow-x-auto"
          style={{
            borderTop: "1px solid rgba(184, 134, 11, 0.1)",
            background: "rgba(255, 255, 255, 0.5)",
          }}
        >
          {Object.entries(CATEGORY_COLORS).map(([cat, color]) => (
            <span
              key={cat}
              className="flex items-center gap-1.5 whitespace-nowrap"
            >
              <span
                className="w-2.5 h-2.5 rounded-full shadow-sm"
                style={{ background: color }}
              />
              <span style={{ color: "#666" }}>
                {cat === "field"
                  ? "领域"
                  : cat === "direction"
                    ? "方向"
                    : cat === "subdirection"
                      ? "子方向"
                      : cat === "task"
                        ? "任务"
                        : cat === "method"
                          ? "方法"
                          : cat === "technique"
                            ? "技术"
                            : cat === "dataset"
                              ? "数据集"
                              : cat === "finding"
                                ? "发现"
                                : cat}
              </span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
