// frontend/src/lib/api/graph.ts
import api from './client'

export const graphApi = {
  stats: () => api.get('/graph/stats'),
  data: (folder?: string) => api.get('/graph/data', { params: { folder } }),
  treeData: () => api.get('/graph/tree-data'),
}