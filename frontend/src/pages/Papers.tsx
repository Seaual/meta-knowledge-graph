import { useEffect, useState, useRef } from "react";
import {
  Upload,
  FileText,
  Trash2,
  Play,
  RefreshCw,
  CheckCircle,
  XCircle,
  Loader2,
  FolderPlus,
  Folder,
  GitBranch,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { papersApi, foldersApi, batchApi } from "../lib/api";
import CreateFolderModal from "../components/CreateFolderModal";
import { useTranslation } from "../i18n";

interface Paper {
  doi: string;
  title: string;
  abstract: string | null;
  authors: string[];
  status: string;
  created_at: string;
  s2_doi?: string;
  venue?: string;
  year?: number;
  citation_count?: number;
  tldr?: string;
  s2_fields_of_study?: string[];
}

interface FolderItem {
  id: string;
  name: string;
  paper_count: number;
}

interface UploadResult {
  filename: string;
  success: boolean;
  title?: string;
  status?: string;
  message?: string;
  error?: string;
}

interface Contribution {
  node_count: number;
  root_concept?: string;
}

interface QueueState {
  total: number; // 初始总数，固定不变
  pending: string[];
  current: string | null;
  completed: number;
  successful: number;
  failed: number;
  estimatedTime: number;
  avgTimePerPaper: number;
  durations: number[];
}

export default function Papers() {
  const { t } = useTranslation();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState<UploadResult[]>([]);
  const [processing, setProcessing] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [queueState, setQueueState] = useState<QueueState>({
    total: 0,
    pending: [],
    current: null,
    completed: 0,
    successful: 0,
    failed: 0,
    estimatedTime: 0,
    avgTimePerPaper: 0,
    durations: [],
  });

  // Folder state
  const [folders, setFolders] = useState<FolderItem[]>([]);
  const [activeFolder, setActiveFolder] = useState<string>("");
  const [showCreateFolder, setShowCreateFolder] = useState(false);
  const [contributions, setContributions] = useState<
    Record<string, Contribution>
  >({});
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  const uploadTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [totalPaperCount, setTotalPaperCount] = useState(0);

  const loadPapers = () => {
    papersApi
      .list(undefined, activeFolder)
      .then((res) => {
        setPapers(res.data);
        setLoading(false);
        loadContributions(res.data);
      })
      .catch((err) => {
        console.error("Failed to load papers:", err);
        setLoading(false);
      });
  };

  const loadFolders = () => {
    foldersApi.list().then((res) => {
      setFolders(res.data);
      // 从 graph stats 获取真实的总数
      papersApi.list().then((papersRes) => {
        setTotalPaperCount(papersRes.data.length);
      });
    });
  };

  const loadContributions = async (paperList: Paper[]) => {
    const results: Record<string, Contribution> = {};
    for (const paper of paperList) {
      if (paper.status === "processed") {
        try {
          const res = await papersApi.contribution(paper.doi);
          results[paper.doi] = res.data;
        } catch {
          results[paper.doi] = { node_count: 0, root_concept: undefined };
        }
      }
    }
    setContributions(results);
  };

  useEffect(() => {
    loadPapers();
    loadFolders();
  }, [activeFolder]);

  // Auto-dismiss upload results after 5 seconds
  useEffect(() => {
    if (uploadResults.length === 0) return;

    if (uploadTimerRef.current) {
      clearTimeout(uploadTimerRef.current);
    }

    uploadTimerRef.current = setTimeout(() => {
      setUploadResults([]);
      uploadTimerRef.current = null;
    }, 5000);

    return () => {
      if (uploadTimerRef.current) {
        clearTimeout(uploadTimerRef.current);
      }
    };
  }, [uploadResults]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    setUploadResults([]);
    const results: UploadResult[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      try {
        const res = await papersApi.upload(file, activeFolder);
        results.push({
          filename: file.name,
          success: true,
          title: res.data.title,
          status: res.data.status,
          message: res.data.message,
        });
      } catch (err: any) {
        const errorMsg =
          err.response?.data?.detail || err.message || "Upload failed";
        results.push({
          filename: file.name,
          success: false,
          error: errorMsg,
        });
      }
    }

    setUploadResults(results);
    setUploading(false);
    loadPapers();
    loadFolders();

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleBatchProcess = async () => {
    const pendingPapers = papers.filter((p) => p.status === "pending");
    if (pendingPapers.length === 0) {
      alert(t.papers.noPapers);
      return;
    }

    if (queueState.current !== null) {
      alert(t.papers.batchProcessing);
      return;
    }

    if (!confirm(`${t.papers.batchProcess} ${pendingPapers.length} papers?`)) {
      return;
    }

    const dois = pendingPapers.map((p) => p.doi);
    const batchSize = 5;
    const newDurations: number[] = [];
    let successful = 0;
    let failed = 0;

    setQueueState({
      total: dois.length,
      pending: dois,
      current: "processing",
      completed: 0,
      successful: 0,
      failed: 0,
      estimatedTime: 0,
      avgTimePerPaper: 0,
      durations: [],
    });

    // 每 5 个一批处理
    for (let i = 0; i < dois.length; i += batchSize) {
      const batch = dois.slice(i, i + batchSize);
      const batchStart = Date.now();

      setQueueState((prev) => ({
        ...prev,
        current: `处理第 ${i + 1}-${Math.min(i + batchSize, dois.length)} 篇`,
        pending: dois.slice(i + batchSize),
        completed: i,
        avgTimePerPaper:
          newDurations.length > 0
            ? newDurations.reduce((a, b) => a + b, 0) / newDurations.length
            : 0,
      }));

      try {
        const jobId = `batch_${Date.now()}_${i}`;
        const res = await batchApi.process(jobId, batch);
        const batchDuration = (Date.now() - batchStart) / 1000;

        // 记录这批的平均时间（每篇）
        const avgBatchTime = batchDuration / batch.length;
        if (newDurations.length >= 50) {
          newDurations.shift();
        }
        newDurations.push(avgBatchTime);

        successful += res.data.successful;
        failed += res.data.failed;

        const avgTime =
          newDurations.reduce((a, b) => a + b, 0) / newDurations.length;
        const remaining = dois.length - i - batch.length;

        setQueueState((prev) => ({
          ...prev,
          completed: i + batch.length,
          successful,
          failed,
          durations: [...newDurations],
          avgTimePerPaper: avgTime,
          estimatedTime: Math.ceil(avgTime * remaining),
        }));
      } catch (err) {
        console.error("Batch process failed:", err);
        failed += batch.length;
      }
    }

    setQueueState((prev) => ({
      ...prev,
      current: null,
    }));

    loadPapers();
    loadFolders();
  };

  const handleProcess = async (doi: string) => {
    setProcessing(doi);
    try {
      const res = await papersApi.process(doi);
      if (res.data.success) {
        loadPapers();
      } else {
        alert(res.data.message);
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || "Processing failed");
    } finally {
      setProcessing(null);
    }
  };

  const handleDelete = async (doi: string) => {
    if (!confirm(`${t.common.delete}?`)) return;
    try {
      await papersApi.delete(doi);
      loadPapers();
      loadFolders();
    } catch {
      alert("Delete failed");
    }
  };

  const handleCreateFolder = async (name: string, description: string) => {
    try {
      await foldersApi.create({ name, description });
      loadFolders();
      setShowCreateFolder(false);
    } catch {
      alert("Create failed");
    }
  };

  const handleDeleteFolder = async (folderId: string) => {
    if (!confirm(`${t.common.delete}?`)) return;
    try {
      await foldersApi.delete(folderId);
      if (activeFolder === folderId) setActiveFolder("");
      loadFolders();
      loadPapers();
    } catch {
      alert("Delete failed");
    }
  };

  const getStatusBadgeClass = (status: string) => {
    const classes: Record<string, string> = {
      pending: "badge-pending",
      downloaded: "badge-processing",
      processed: "badge-success",
      failed: "badge-error",
    };
    return classes[status] || "badge-processing";
  };

  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (minutes < 60) return `${minutes}m${secs > 0 ? secs + "s" : ""}`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h${mins > 0 ? mins + "m" : ""}`;
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="loading-academic">{t.common.loading}</div>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-64px)]">
      {/* Sidebar - Academic Style */}
      <div
        className={`sidebar-academic flex flex-col transition-all duration-300 ${sidebarCollapsed ? "w-12" : "w-64"}`}
      >
        {/* Collapse Toggle */}
        <div className="p-2 border-b border-academic flex justify-end">
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="w-7 h-7 rounded-soft text-muted hover:text-sepia hover:bg-vellum transition-all flex items-center justify-center"
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {!sidebarCollapsed && (
          <>
            <div className="px-4 py-3 border-b border-academic">
              <h2 className="font-mono text-xs text-muted uppercase tracking-wider flex items-center gap-2">
                <Folder className="w-4 h-4" />
                {t.papers.collections}
              </h2>
            </div>

            <div className="flex-1 overflow-y-auto py-2">
              {/* All papers option */}
              <div
                className={`sidebar-item flex items-center justify-between ${
                  activeFolder === "" ? "active" : ""
                }`}
                onClick={() => setActiveFolder("")}
              >
                <div className="flex items-center gap-2">
                  <Folder className="w-4 h-4" />
                  <span className="font-body text-sm">
                    {t.papers.allPapers}
                  </span>
                </div>
                <span className="font-mono text-xs text-faint">
                  {totalPaperCount}
                </span>
              </div>

              {folders.map((folder) => (
                <div
                  key={folder.id}
                  className={`sidebar-item flex items-center justify-between ${
                    activeFolder === folder.id ? "active" : ""
                  }`}
                  onClick={() => setActiveFolder(folder.id)}
                >
                  <div className="flex items-center gap-2">
                    <Folder className="w-4 h-4" />
                    <span className="font-body text-sm">{folder.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-faint">
                      {folder.paper_count}
                    </span>
                    {folder.id !== "default" && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteFolder(folder.id);
                        }}
                        className="w-5 h-5 rounded-soft text-faint hover:text-status-error hover:bg-red-50 flex items-center justify-center"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="p-4 border-t border-academic">
              <button
                onClick={() => setShowCreateFolder(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 border-2 border-dashed border-academic rounded-medium font-body text-sm text-muted hover:text-sepia hover:border-sepia hover:bg-vellum transition-all"
              >
                <FolderPlus className="w-4 h-4" />
                {t.papers.newCollection}
              </button>
            </div>
          </>
        )}

        {sidebarCollapsed && (
          <div className="flex-1 flex flex-col items-center py-2 gap-1">
            <button
              onClick={() => {
                setActiveFolder("");
                setSidebarCollapsed(false);
              }}
              className={`w-8 h-8 rounded-soft flex items-center justify-center transition-all ${
                activeFolder === ""
                  ? "bg-vellum text-sepia"
                  : "text-muted hover:bg-vellum"
              }`}
              title={t.papers.allPapers}
            >
              <Folder className="w-4 h-4" />
            </button>

            {folders.map((folder) => (
              <button
                key={folder.id}
                onClick={() => {
                  setActiveFolder(folder.id);
                  setSidebarCollapsed(false);
                }}
                className={`w-8 h-8 rounded-soft flex items-center justify-center transition-all ${
                  activeFolder === folder.id
                    ? "bg-vellum text-sepia"
                    : "text-muted hover:bg-vellum"
                }`}
                title={folder.name}
              >
                <Folder className="w-4 h-4" />
              </button>
            ))}

            <button
              onClick={() => setShowCreateFolder(true)}
              className="w-8 h-8 rounded-soft text-muted hover:text-sepia hover:bg-vellum flex items-center justify-center mt-2"
              title={t.papers.newCollection}
            >
              <FolderPlus className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-8 animate-fade-in">
        <div className="max-w-5xl mx-auto space-y-6">
          {/* Header */}
          <div className="flex justify-between items-center">
            <div>
              <h1 className="font-display text-2xl text-sepia mb-1">
                {t.papers.title}
              </h1>
              <p className="font-body text-sm text-muted">
                {t.papers.subtitle}
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  loadPapers();
                  loadFolders();
                }}
                className="btn-secondary flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                {t.papers.refresh}
              </button>

              {papers.filter((p) => p.status === "pending").length > 0 && (
                <button
                  onClick={handleBatchProcess}
                  disabled={queueState.current !== null}
                  className="btn-primary flex items-center gap-2"
                >
                  {queueState.current !== null ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {t.papers.batchProcessing}
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      {t.papers.batchProcess} (
                      {papers.filter((p) => p.status === "pending").length})
                    </>
                  )}
                </button>
              )}

              <label className="btn-primary flex items-center gap-2 cursor-pointer">
                <Upload className="w-4 h-4" />
                {uploading ? t.papers.uploading : t.papers.uploadPdf}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  multiple
                  className="hidden"
                  onChange={handleUpload}
                  disabled={uploading}
                />
              </label>
            </div>
          </div>

          {/* Upload Results */}
          {uploadResults.length > 0 && (
            <div className="card-academic p-4 animate-slide-down">
              <h3 className="font-mono text-xs text-muted uppercase tracking-wider mb-3">
                {t.papers.uploadResults}
              </h3>
              <div className="space-y-2">
                {uploadResults.map((result, idx) => (
                  <div
                    key={idx}
                    className={`flex items-start gap-3 p-3 rounded-soft ${
                      result.success
                        ? "bg-gradient-to-r from-transparent to-status-success/5"
                        : "bg-gradient-to-r from-transparent to-status-error/5"
                    }`}
                  >
                    {result.success ? (
                      <CheckCircle className="w-4 h-4 text-status-success mt-0.5" />
                    ) : (
                      <XCircle className="w-4 h-4 text-status-error mt-0.5" />
                    )}
                    <div className="flex-1">
                      <div className="font-body font-medium text-sepia">
                        {result.filename}
                      </div>
                      {result.success && result.title && (
                        <div className="font-body text-sm text-muted">
                          {result.title}
                        </div>
                      )}
                      {result.message && (
                        <div
                          className={`font-mono text-xs ${
                            result.status === "processed"
                              ? "text-status-success"
                              : result.status === "pending"
                                ? "text-amber"
                                : "text-muted"
                          }`}
                        >
                          {result.message}
                        </div>
                      )}
                      {!result.success && result.error && (
                        <div className="font-mono text-xs text-status-error">
                          {result.error}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Queue Progress */}
          {(queueState.current !== null || queueState.completed > 0) && (
            <div className="card-academic p-4 animate-slide-down">
              <h3 className="font-mono text-xs text-muted uppercase tracking-wider mb-3">
                {queueState.current !== null
                  ? t.papers.batchProcessing
                  : t.papers.batchComplete}
              </h3>

              <div className="flex items-center gap-4 mb-3">
                <div className="flex-1 h-2 bg-paper rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-amber rounded-full transition-all duration-300"
                    style={{
                      width: `${
                        queueState.total > 0
                          ? (queueState.completed / queueState.total) * 100
                          : 0
                      }%`,
                    }}
                  />
                </div>
                <span className="font-mono text-sm text-muted">
                  {queueState.completed}/{queueState.total}
                </span>
              </div>

              <div className="flex gap-4 font-mono text-xs">
                <span className="text-status-success">
                  {t.papers.progress.success}: {queueState.successful}
                </span>
                <span className="text-status-error">
                  {t.papers.progress.failed}: {queueState.failed}
                </span>
                {queueState.estimatedTime > 0 &&
                  queueState.current !== null && (
                    <span className="text-muted">
                      {t.papers.progress.remaining}:{" "}
                      {formatTime(queueState.estimatedTime)}
                    </span>
                  )}
              </div>
            </div>
          )}

          {/* Paper Table */}
          {papers.length === 0 ? (
            <div className="card-academic p-12 text-center">
              <FileText className="w-12 h-12 mx-auto text-faint mb-4" />
              <p className="font-quote text-lg text-muted italic">
                {t.papers.noPapers}
              </p>
              <p className="font-body text-sm text-faint mt-2">
                {t.papers.noPapersDesc}
              </p>
            </div>
          ) : (
            <div className="card-academic overflow-hidden">
              <table className="table min-w-full">
                <thead>
                  <tr>
                    <th>{t.papers.table.title}</th>
                    <th className="w-24 min-w-[80px]">
                      {t.papers.table.status}
                    </th>
                    <th>{t.papers.table.nodes}</th>
                    <th>{t.papers.table.root}</th>
                    <th className="text-right">{t.papers.table.actions}</th>
                  </tr>
                </thead>
                <tbody>
                  {papers.map((paper) => (
                    <tr key={paper.doi}>
                      <td>
                        <div className="font-body font-medium text-sepia">
                          {paper.title}
                        </div>
                        {paper.authors && paper.authors.length > 0 && (
                          <div className="font-body text-sm text-muted">
                            {Array.isArray(paper.authors)
                              ? paper.authors.slice(0, 3).join(", ")
                              : paper.authors}
                          </div>
                        )}
                        {paper.s2_doi && (
                          <a
                            href={`https://doi.org/${paper.s2_doi}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-mono text-xs text-status-info hover:text-sepia hover:underline"
                          >
                            DOI: {paper.s2_doi}
                          </a>
                        )}
                        {paper.venue && paper.year && (
                          <div className="font-mono text-xs text-faint mt-1">
                            {paper.venue}, {paper.year}
                          </div>
                        )}
                        {paper.tldr && (
                          <div className="font-quote text-xs text-status-success mt-1 italic">
                            TLDR: {paper.tldr}
                          </div>
                        )}
                      </td>
                      <td className="w-24 min-w-[80px]">
                        <span
                          className={`badge-academic ${getStatusBadgeClass(paper.status)}`}
                        >
                          {t.papers.status[
                            paper.status as keyof typeof t.papers.status
                          ] || paper.status}
                        </span>
                      </td>
                      <td>
                        <div className="flex items-center gap-1 text-muted">
                          <GitBranch className="w-3 h-3" />
                          <span className="font-mono text-sm">
                            {paper.status === "processed"
                              ? contributions[paper.doi]?.node_count || "-"
                              : "-"}
                          </span>
                        </div>
                      </td>
                      <td>
                        <span className="font-body text-sm text-muted">
                          {paper.status === "processed"
                            ? contributions[paper.doi]?.root_concept || "-"
                            : "-"}
                        </span>
                      </td>
                      <td className="text-right">
                        <div className="flex justify-end gap-1">
                          {paper.status === "pending" && (
                            <button
                              onClick={() => handleProcess(paper.doi)}
                              disabled={processing === paper.doi}
                              className="w-8 h-8 rounded-soft text-muted hover:text-amber hover:bg-amber/5 disabled:opacity-50 flex items-center justify-center transition-all"
                              title={t.papers.process}
                            >
                              {processing === paper.doi ? (
                                <RefreshCw className="w-4 h-4 animate-spin" />
                              ) : (
                                <Play className="w-4 h-4" />
                              )}
                            </button>
                          )}
                          <button
                            onClick={() => handleDelete(paper.doi)}
                            className="w-8 h-8 rounded-soft text-muted hover:text-status-error hover:bg-red-50 flex items-center justify-center transition-all"
                            title={t.common.delete}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Create Folder Modal */}
      {showCreateFolder && (
        <CreateFolderModal
          onClose={() => setShowCreateFolder(false)}
          onCreate={handleCreateFolder}
        />
      )}
    </div>
  );
}
