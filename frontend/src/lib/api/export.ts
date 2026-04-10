// frontend/src/lib/api/export.ts
import api from "./client";

export interface ExportResponse {
  content: string;
  stats: {
    papers: number;
    concepts: number;
    generated_at: string;
  };
}

export const exportApi = {
  obsidian: (folderId?: string) =>
    api.get<ExportResponse>("/graph/export/obsidian", {
      params: { folder_id: folderId },
    }),
  download: (folderId?: string) =>
    api.get("/graph/export/obsidian/download", {
      params: { folder_id: folderId },
      responseType: "blob",
    }),
  canvas: (folderId?: string) =>
    api.get("/graph/export/obsidian/canvas", {
      params: { folder_id: folderId },
    }),
  downloadCanvas: (folderId?: string) =>
    api.get("/graph/export/obsidian/canvas/download", {
      params: { folder_id: folderId },
      responseType: "blob",
    }),
  html: (folderId?: string) =>
    api.get("/graph/export/obsidian/html", { params: { folder_id: folderId } }),
  downloadHtml: (folderId?: string) =>
    api.get("/graph/export/obsidian/html/download", {
      params: { folder_id: folderId },
      responseType: "blob",
    }),
};
