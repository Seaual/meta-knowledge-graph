// frontend/src/pages/ConceptsGraph/hooks/useGraph.ts

import { useState, useEffect, useCallback } from "react";
import { conceptsApi, graphApi, papersApi, foldersApi } from "../../../lib/api";
import { useAgentStore } from "../../../stores/agentStore";
import type {
  Concept,
  Paper,
  GraphNode,
  GraphEdge,
  ResearchPointsResponse,
} from "../types";

interface UseGraphReturn {
  // Data
  loading: boolean;
  concepts: Concept[];
  edges: GraphEdge[];
  graphNodes: GraphNode[];
  graphLinks: { source: string; target: string }[];
  folders: { id: string; name: string }[];

  // View state
  viewMode: "all" | "concept";
  selectedConcept: Concept | null;
  selectedPaper: Paper | null;
  activeFolder: string;
  forceStrength: number;
  setForceStrength: (value: number) => void;

  // Research points
  researchPoints: ResearchPointsResponse | null;
  loadingResearchPoints: boolean;

  // Actions
  handleConceptClick: (node: GraphNode) => Promise<void>;
  handlePaperClick: (node: GraphNode) => Promise<void>;
  handleViewPapers: () => void;
  handleBack: () => void;
  handleDiscoverResearchPoints: () => Promise<void>;
  setActiveFolder: (folder: string) => void;
  loadFolders: () => void;

  // Graph methods
  getNodeDepth: (nodeId: string, parentMap: Map<string, string>) => number;
  setSelectedConcept: (concept: Concept | null) => void;
  setSelectedPaper: (paper: Paper | null) => void;
  setResearchPoints: (points: ResearchPointsResponse | null) => void;
  setLoadingResearchPoints: (loading: boolean) => void;
}

export function useGraph(): UseGraphReturn {
  // Agent store for context
  const { updateContext } = useAgentStore();

  // Data state
  const [loading, setLoading] = useState(true);
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [graphLinks, setGraphLinks] = useState<
    { source: string; target: string }[]
  >([]);
  const [folders, setFolders] = useState<{ id: string; name: string }[]>([]);

  // View state
  const [viewMode, setViewMode] = useState<"all" | "concept">("all");
  const [selectedConcept, setSelectedConcept] = useState<Concept | null>(null);
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [activeFolder, setActiveFolder] = useState<string>("");
  const [forceStrength, setForceStrength] = useState(150);

  // Research points state
  const [researchPoints, setResearchPoints] =
    useState<ResearchPointsResponse | null>(null);
  const [loadingResearchPoints, setLoadingResearchPoints] = useState(false);

  // Compute depth for each node
  const getNodeDepth = useCallback(
    (nodeId: string, parentMap: Map<string, string>): number => {
      const visited = new Set<string>();
      let depth = 0;
      let current = nodeId;
      while (parentMap.has(current) && !visited.has(current)) {
        visited.add(current);
        depth++;
        current = parentMap.get(current)!;
      }
      return depth;
    },
    []
  );

  // Load folders
  const loadFolders = useCallback(() => {
    foldersApi.list().then((res) => {
      setFolders(res.data);
    });
  }, []);

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      try {
        const graphRes = await graphApi.data(activeFolder);
        const nodesFromGraph = graphRes.data.nodes.map(
          (n: {
            id: string;
            label: string;
            label_en?: string;
            category?: string;
            paper_count?: number;
          }) => ({
            id: n.id,
            text: n.label,
            text_en: n.label_en,
            category: n.category,
            paper_count: n.paper_count || 0,
          })
        );
        setConcepts(nodesFromGraph);
        setEdges(graphRes.data.edges);
        setLoading(false);
      } catch (err) {
        console.error("Failed to load:", err);
        setLoading(false);
      }
    };
    loadData();
    loadFolders();
  }, [activeFolder, loadFolders]);

  // Build initial graph data
  useEffect(() => {
    if (loading || concepts.length === 0) return;

    const parentMap = new Map<string, string>();
    edges.forEach((e) => parentMap.set(e.target, e.source));

    const nodes: GraphNode[] = concepts.map((c) => ({
      id: c.id,
      name: c.text,
      name_en: c.text_en,
      type: "concept" as const,
      category: c.category || "method",
      paperCount: c.paper_count,
      depth: getNodeDepth(c.id, parentMap),
    }));

    const links = edges.map((e) => ({
      source: e.source,
      target: e.target,
    }));

    setGraphNodes(nodes);
    setGraphLinks(links);
    setViewMode("all");
  }, [loading, concepts, edges, getNodeDepth]);

  // Handle concept click
  const handleConceptClick = useCallback(
    async (node: GraphNode) => {
      if (node.type !== "concept") return;

      try {
        const res = await conceptsApi.get(node.id);
        setSelectedConcept(res.data);
        setSelectedPaper(null);

        // Update AI Agent context
        updateContext({
          currentTarget: {
            type: "concept",
            id: res.data.id,
            name: res.data.text,
          },
        });
      } catch (err) {
        console.error("Failed to get concept:", err);
      }
    },
    [updateContext]
  );

  // Enter paper view
  const handleViewPapers = useCallback(() => {
    if (!selectedConcept) return;

    const papers = selectedConcept.papers || [];
    if (papers.length === 0) return;

    const centerNode: GraphNode = {
      id: `center-${selectedConcept.id}`,
      name: selectedConcept.text,
      type: "center",
      category: selectedConcept.category ?? undefined,
      paperCount: selectedConcept.paper_count,
    };

    const paperNodes: GraphNode[] = papers.map(
      (p: { doi: string; title: string }) => ({
        id: `paper-${p.doi}`,
        name: p.title,
        type: "paper" as const,
        doi: p.doi,
      })
    );

    const paperLinks = papers.map((p: { doi: string }) => ({
      source: centerNode.id,
      target: `paper-${p.doi}`,
    }));

    setGraphNodes([centerNode, ...paperNodes]);
    setGraphLinks(paperLinks);
    setViewMode("concept");
    setSelectedPaper(null);
  }, [selectedConcept]);

  // Handle paper click
  const handlePaperClick = useCallback(
    async (node: GraphNode) => {
      if (node.type !== "paper" || !node.doi) return;

      try {
        const res = await papersApi.get(node.doi);
        setSelectedPaper(res.data);

        // Update AI Agent context
        updateContext({
          currentTarget: {
            type: "paper",
            id: node.doi,
            name: res.data.title,
          },
        });
      } catch (err) {
        console.error("Failed to get paper:", err);
      }
    },
    [updateContext]
  );

  // Discover research points
  const handleDiscoverResearchPoints = useCallback(async () => {
    if (!selectedConcept) return;

    setLoadingResearchPoints(true);
    setResearchPoints(null);

    try {
      const res = await conceptsApi.researchPoints(selectedConcept.id);
      setResearchPoints(res.data);
    } catch (err) {
      console.error("Failed to get research points:", err);
      setResearchPoints({
        concept_id: selectedConcept.id,
        concept_name: selectedConcept.text,
        research_points: [
          {
            title: "Analysis Failed",
            hypothesis: "",
            description:
              "Could not retrieve research points. Check LLM configuration.",
            discovery_method: "gap_filling",
            rationale: String(err),
            related_concepts: [],
            difficulty: "medium",
            difficulty_reason: "Analysis failed",
            novelty: "moderate",
            potential_impact: "niche",
          },
        ],
        analysis_context: {
          concept: { id: selectedConcept.id, name: selectedConcept.text },
          ancestors: [],
          descendants: [],
          edge_nodes: [],
          related_papers: [],
        },
      });
    } finally {
      setLoadingResearchPoints(false);
    }
  }, [selectedConcept]);

  // Back to all concepts
  const handleBack = useCallback(() => {
    const parentMap = new Map<string, string>();
    edges.forEach((e) => parentMap.set(e.target, e.source));

    const nodes: GraphNode[] = concepts.map((c) => ({
      id: c.id,
      name: c.text,
      name_en: c.text_en,
      type: "concept" as const,
      category: c.category || "method",
      paperCount: c.paper_count,
      depth: getNodeDepth(c.id, parentMap),
    }));

    const links = edges.map((e) => ({
      source: e.source,
      target: e.target,
    }));

    setGraphNodes(nodes);
    setGraphLinks(links);
    setViewMode("all");
    setSelectedConcept(null);
    setSelectedPaper(null);
    setResearchPoints(null);
  }, [concepts, edges, getNodeDepth]);

  return {
    // Data
    loading,
    concepts,
    edges,
    graphNodes,
    graphLinks,
    folders,

    // View state
    viewMode,
    selectedConcept,
    selectedPaper,
    activeFolder,
    forceStrength,
    setForceStrength,

    // Research points
    researchPoints,
    loadingResearchPoints,

    // Actions
    handleConceptClick,
    handlePaperClick,
    handleViewPapers,
    handleBack,
    handleDiscoverResearchPoints,
    setActiveFolder,
    loadFolders,

    // Graph methods
    getNodeDepth,
    setSelectedConcept,
    setSelectedPaper,
    setResearchPoints,
    setLoadingResearchPoints,
  };
}
