// frontend/src/lib/api/concepts.ts
import api from "./client";

export const conceptsApi = {
  list: () => api.get("/concepts/"),
  roots: () => api.get("/concepts/roots"),
  tree: (rootId?: string) =>
    api.get("/concepts/tree", { params: { root_id: rootId } }),
  search: (q: string) => api.get("/concepts/search", { params: { q } }),
  get: (id: string) => api.get(`/concepts/${id}`),
  papers: (id: string) => api.get(`/concepts/${id}/papers`),
  researchPoints: (id: string) => api.get(`/concepts/${id}/research-points`),
};
