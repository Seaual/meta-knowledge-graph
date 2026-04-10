// frontend/src/pages/ConceptsGraph/types.ts

export interface Concept {
  id: string;
  text: string;
  text_en?: string;
  category: string | null | undefined;
  paper_count: number;
  parents?: Concept[];
  children?: Concept[];
  papers?: { doi: string; title: string }[];
}

export interface Paper {
  doi: string;
  title: string;
  authors?: string[];
  keywords?: string[];
  contributions?: string[];
  abstract: string | null;
  status: string;
  s2_doi?: string;
  venue?: string;
  year?: number;
  citation_count?: number;
  tldr?: string;
  s2_fields_of_study?: string[];
}

export interface GraphEdge {
  source: string;
  target: string;
}

export type NodeType = "concept" | "paper" | "center";

export interface GraphNode {
  id: string;
  name: string;
  name_en?: string;
  type: NodeType;
  category?: string;
  paperCount?: number;
  depth?: number;
  authors?: string[];
  keywords?: string[];
  abstract?: string | null;
  doi?: string;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number;
  fy?: number;
}

export interface ResearchPoint {
  title: string;
  hypothesis: string;
  description: string;
  discovery_method:
    | "gap_filling"
    | "leaf_extension"
    | "bottleneck"
    | "transfer";
  rationale: string;
  related_concepts: string[];
  difficulty: "low" | "medium" | "high";
  difficulty_reason: string;
  novelty: "incremental" | "moderate" | "high";
  potential_impact: "niche" | "broad" | "transformative";
}

export interface ResearchPointsResponse {
  concept_id: string;
  concept_name: string;
  research_points: ResearchPoint[];
  analysis_context: {
    concept: { id: string; name: string; category?: string };
    ancestors: { id: string; name: string; category?: string }[];
    descendants: {
      id: string;
      name: string;
      category?: string;
      depth?: number;
    }[];
    edge_nodes: { id: string; name: string; category?: string }[];
    related_papers: { title: string; keywords?: string[] }[];
  };
}
