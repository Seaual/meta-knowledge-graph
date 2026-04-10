// frontend/src/lib/api/s2.ts
import api from "./client";

// S2 Configuration types
export interface S2ConfigResponse {
  has_api_key: boolean;
  enabled: boolean;
  masked_key?: string;
}

export interface S2ConfigRequest {
  api_key: string;
  enabled?: boolean;
}

export interface S2TestResponse {
  success: boolean;
  message: string;
}

// S2 Recommendation types
export interface RecommendedPaper {
  paperId: string;
  title: string;
  abstract?: string;
  year?: number;
  citationCount?: number;
  authors?: Array<{ name: string }>;
  venue?: string;
  openAccessPdf?: { url: string };
  tldr?: { text: string };
}

export interface RecommendationsResponse {
  recommendations: RecommendedPaper[];
  based_on: string[];
}

export interface ConceptSearchPapersResponse {
  concept_id: string;
  concept_text: string;
  concept_text_zh?: string;
  concept_text_en?: string;
  papers: RecommendedPaper[];
  total: number;
}

// S2 Paper Add types
export interface AddFromS2Request {
  s2_paper_id: string;
  title: string;
  year?: number;
  abstract?: string;
  authors?: Array<{ name: string }>;
  venue?: string;
  citation_count?: number;
  tldr?: { text: string };
  open_access_pdf_url?: string;
}

export interface AddFromS2Response {
  success: boolean;
  message: string;
  doi?: string;
  title?: string;
  concepts_count?: number;
}

// Semantic Scholar API
export const s2Api = {
  getConfig: () => api.get<S2ConfigResponse>("/s2/config"),
  saveConfig: (data: S2ConfigRequest) =>
    api.post<S2ConfigResponse>("/s2/config", data),
  test: (apiKey: string) =>
    api.post<S2TestResponse>("/s2/test", { api_key: apiKey }),
  enhance: (doi: string) =>
    api.post(`/s2/papers/${encodeURIComponent(doi)}/enhance`),
};

// S2 Recommendation API
export const recommendationApi = {
  getGraphRecommendations: () =>
    api.get<RecommendationsResponse>("/recommendations"),
  searchPapersByConcept: (
    conceptId: string,
    year?: string,
    minCitations?: number,
    limit?: number
  ) =>
    api.get<ConceptSearchPapersResponse>(
      `/concepts/${conceptId}/search-papers`,
      {
        params: { year, min_citations: minCitations, limit },
      }
    ),
  searchPapersByConcepts: async (
    _conceptIds: string[],
    conceptTexts: string[]
  ) => {
    const query = conceptTexts.join(" ");
    const res = await api.get<{ papers: RecommendedPaper[]; total: number }>(
      "/s2/search",
      {
        params: { query, limit: 20 },
      }
    );
    return res;
  },
};

// S2 Paper Add API
export const s2PaperApi = {
  addMetadata: (data: AddFromS2Request) =>
    api.post<AddFromS2Response>("/papers/add-from-s2", {
      ...data,
      authors: data.authors?.map((a) => a.name),
      tldr: data.tldr?.text,
    }),
  downloadAndProcess: (
    data: AddFromS2Request & { open_access_pdf_url: string }
  ) =>
    api.post<AddFromS2Response>("/papers/download-and-process", {
      ...data,
      authors: data.authors?.map((a) => a.name),
      tldr: data.tldr?.text,
    }),
};
