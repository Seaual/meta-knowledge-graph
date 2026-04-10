// frontend/src/components/MiniConceptGraph.tsx
// 迷你概念图谱组件 - 在聊天消息中嵌入

import { useEffect, useRef } from "react";
import ForceGraph from "force-graph";
import { ConceptNode } from "../stores/agentStore";

interface Props {
  data: ConceptNode;
  width?: number;
  height?: number;
  onNodeClick?: (node: ConceptNode) => void;
}

const CENTER_COLOR = "#d4a012"; // gold
const PARENT_COLOR = "#6b4423"; // sepia
const CHILD_COLOR = "#4a6b8a"; // slate blue

export default function MiniConceptGraph({
  data,
  width = 320,
  height = 180,
  onNodeClick,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current || !data) return;

    // 构建节点和边
    const nodes: any[] = [
      {
        id: data.id,
        name: data.name,
        type: "center",
        paperCount: data.paper_count,
        category: data.category,
      },
    ];

    const links: { source: string; target: string }[] = [];

    // 添加子概念
    data.children?.forEach((child) => {
      nodes.push({
        id: child.id,
        name: child.name,
        type: "child",
        paperCount: child.paper_count,
        category: child.category,
      });
      links.push({ source: data.id, target: child.id });
    });

    // 添加父概念
    data.parents?.forEach((parent) => {
      nodes.push({
        id: parent.id,
        name: parent.name,
        type: "parent",
        paperCount: parent.paper_count,
        category: parent.category,
      });
      links.push({ source: parent.id, target: data.id });
    });

    // 销毁旧图谱
    if (graphRef.current) {
      graphRef.current._destructor();
    }

    // 创建迷你图谱
    const graph = new ForceGraph(containerRef.current)
      .graphData({ nodes, links })
      .width(width)
      .height(height)
      .nodeId("id")
      .nodeLabel((node: any) => `${node.name} (${node.paperCount || 0} papers)`)
      .nodeColor((node: any) => {
        if (node.type === "center") return CENTER_COLOR;
        if (node.type === "parent") return PARENT_COLOR;
        return CHILD_COLOR;
      })
      .nodeCanvasObject(
        (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const size = node.type === "center" ? 6 : 4;
          const x = node.x;
          const y = node.y;

          // 绘制节点
          ctx.beginPath();
          ctx.arc(x, y, size, 0, 2 * Math.PI);
          ctx.fillStyle =
            node.type === "center"
              ? CENTER_COLOR
              : node.type === "parent"
                ? PARENT_COLOR
                : CHILD_COLOR;
          ctx.fill();

          // 中心节点显示名称
          if (node.type === "center" && globalScale > 0.8) {
            ctx.font = "10px Inter, sans-serif";
            ctx.fillStyle = "#2c1810";
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            const displayName =
              node.name.length > 15
                ? node.name.slice(0, 15) + "..."
                : node.name;
            ctx.fillText(displayName, x, y + size + 3);
          }
        }
      )
      .linkColor(() => "rgba(184, 134, 11, 0.25)")
      .linkWidth(1)
      .cooldownTicks(50)
      .d3AlphaDecay(0.05)
      .d3VelocityDecay(0.4)
      .enableZoomInteraction(true) // 启用缩放
      .enableNodeDrag(true) // 启用节点拖拽
      .minZoom(0.5)
      .maxZoom(3)
      .onNodeClick((node: any) => {
        if (onNodeClick && node) {
          onNodeClick({
            id: node.id,
            name: node.name,
            category: node.category,
            paper_count: node.paperCount || 0,
          });
        }
      });

    graphRef.current = graph;

    return () => {
      if (graphRef.current) {
        graphRef.current._destructor();
        graphRef.current = null;
      }
    };
  }, [data, width, height, onNodeClick]);

  return (
    <div className="mini-concept-graph">
      <div
        ref={containerRef}
        style={{
          width,
          height,
          borderRadius: "8px",
          background: "rgba(245, 240, 232, 0.03)",
          border: "1px solid rgba(184, 134, 11, 0.1)",
        }}
      />
      {/* 图例 */}
      <div
        className="flex items-center justify-center gap-4 mt-2 text-[10px]"
        style={{ color: "var(--color-muted)" }}
      >
        <span className="flex items-center gap-1">
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: PARENT_COLOR }}
          />
          父概念
        </span>
        <span className="flex items-center gap-1">
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: CENTER_COLOR }}
          />
          当前
        </span>
        <span className="flex items-center gap-1">
          <span
            className="w-2 h-2 rounded-full"
            style={{ background: CHILD_COLOR }}
          />
          子概念
        </span>
      </div>
    </div>
  );
}
