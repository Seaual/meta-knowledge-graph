// frontend/src/lib/api/folders.ts
import api from "./client";

export interface FolderResponse {
  id: string;
  name: string;
  description?: string;
  paper_count: number;
  created_at?: string;
}

export interface CreateFolderRequest {
  name: string;
  description?: string;
}

export interface UpdateFolderRequest {
  name?: string;
  description?: string;
}

export const foldersApi = {
  list: () => api.get<FolderResponse[]>("/folders/"),
  create: (data: CreateFolderRequest) =>
    api.post<FolderResponse>("/folders/", data),
  update: (id: string, data: UpdateFolderRequest) =>
    api.patch<FolderResponse>(`/folders/${id}`, data),
  delete: (id: string) => api.delete(`/folders/${id}`),
};
