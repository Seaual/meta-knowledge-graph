import { useEffect, useState, useRef } from 'react'
import { Upload, FileText, Trash2, Play, RefreshCw, CheckCircle, XCircle, Loader2, FolderPlus, Folder, GitBranch, ChevronLeft, ChevronRight } from 'lucide-react'
import { papersApi, foldersApi } from '../lib/api'
import CreateFolderModal from '../components/CreateFolderModal'

interface Paper {
  doi: string
  title: string
  abstract: string | null
  authors: string[]
  status: string
  created_at: string
}

interface FolderItem {
  id: string
  name: string
  paper_count: number
}

interface UploadResult {
  filename: string
  success: boolean
  title?: string
  status?: string
  message?: string
  error?: string
}

interface Contribution {
  node_count: number
  root_concept?: string
}

interface QueueState {
  pending: string[]
  current: string | null
  completed: number
  successful: number
  failed: number
  estimatedTime: number
  avgTimePerPaper: number
  durations: number[]
}

export default function Papers() {
  const [papers, setPapers] = useState<Paper[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadResults, setUploadResults] = useState<UploadResult[]>([])
  const [processing, setProcessing] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const MAX_DURATIONS = 50
  const [queueState, setQueueState] = useState<QueueState>({
    pending: [],
    current: null,
    completed: 0,
    successful: 0,
    failed: 0,
    estimatedTime: 0,
    avgTimePerPaper: 0,
    durations: []
  })

  // Folder state
  const [folders, setFolders] = useState<FolderItem[]>([])
  const [activeFolder, setActiveFolder] = useState('default')
  const [showCreateFolder, setShowCreateFolder] = useState(false)
  const [contributions, setContributions] = useState<Record<string, Contribution>>({})
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const uploadTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const loadPapers = () => {
    papersApi.list(undefined, activeFolder).then(res => {
      setPapers(res.data)
      setLoading(false)
      loadContributions(res.data)
    }).catch(err => {
      console.error('Failed to load papers:', err)
      setLoading(false)
    })
  }

  const loadFolders = () => {
    foldersApi.list().then(res => {
      setFolders(res.data)
    })
  }

  const loadContributions = async (paperList: Paper[]) => {
    const results: Record<string, Contribution> = {}
    for (const paper of paperList) {
      if (paper.status === 'processed') {
        try {
          const res = await papersApi.contribution(paper.doi)
          results[paper.doi] = res.data
        } catch {
          results[paper.doi] = { node_count: 0, root_concept: undefined }
        }
      }
    }
    setContributions(results)
  }

  useEffect(() => {
    loadPapers()
    loadFolders()
  }, [activeFolder])

  // Auto-dismiss upload results after 5 seconds
  useEffect(() => {
    if (uploadResults.length === 0) return

    // Clear old timer
    if (uploadTimerRef.current) {
      clearTimeout(uploadTimerRef.current)
    }

    // Set new timer
    uploadTimerRef.current = setTimeout(() => {
      setUploadResults([])
      uploadTimerRef.current = null
    }, 5000)

    return () => {
      if (uploadTimerRef.current) {
        clearTimeout(uploadTimerRef.current)
      }
    }
  }, [uploadResults])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setUploading(true)
    setUploadResults([])
    const results: UploadResult[] = []

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      try {
        const res = await papersApi.upload(file, activeFolder)
        results.push({
          filename: file.name,
          success: true,
          title: res.data.title,
          status: res.data.status,
          message: res.data.message
        })
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || err.message || '上传失败'
        results.push({
          filename: file.name,
          success: false,
          error: errorMsg
        })
      }
    }

    setUploadResults(results)
    setUploading(false)
    loadPapers()
    loadFolders()

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleBatchProcess = async () => {
    const pendingPapers = papers.filter(p => p.status === 'pending')
    if (pendingPapers.length === 0) {
      alert('没有待处理的论文')
      return
    }

    // Check if already processing
    if (queueState.current !== null) {
      alert('已有批量处理任务进行中，请等待完成')
      return
    }

    if (!confirm(`确定要处理 ${pendingPapers.length} 篇论文？\n这将按顺序逐个处理，显示实时进度。`)) {
      return
    }

    // Initialize queue
    const dois = pendingPapers.map(p => p.doi)
    setQueueState({
      pending: dois,
      current: dois[0],
      completed: 0,
      successful: 0,
      failed: 0,
      estimatedTime: 0,
      avgTimePerPaper: 0,
      durations: []
    })

    // Process sequentially
    const newDurations: number[] = []
    let successful = 0
    let failed = 0

    for (let i = 0; i < dois.length; i++) {
      const doi = dois[i]

      setQueueState(prev => ({
        ...prev,
        current: doi,
        pending: dois.slice(i + 1),
        completed: i,
        avgTimePerPaper: newDurations.length > 0
          ? newDurations.reduce((a, b) => a + b, 0) / newDurations.length
          : 0
      }))

      try {
        const res = await papersApi.processSingle(doi)
        const duration = res.data.duration

        // Limit durations array
        if (newDurations.length >= MAX_DURATIONS) {
          newDurations.shift()
        }
        newDurations.push(duration)

        if (res.data.success) {
          successful++
        } else {
          failed++
        }
      } catch (err) {
        failed++
        console.error(`Failed to process ${doi}:`, err)
      }

      // Update progress
      const avgTime = newDurations.length > 0
        ? newDurations.reduce((a, b) => a + b, 0) / newDurations.length
        : 0
      const remaining = dois.length - i - 1

      setQueueState(prev => ({
        ...prev,
        completed: i + 1,
        successful,
        failed,
        durations: [...newDurations],
        avgTimePerPaper: avgTime,
        estimatedTime: Math.ceil(avgTime * remaining)
      }))
    }

    // Finish
    setQueueState(prev => ({
      ...prev,
      current: null
    }))

    loadPapers()
    loadFolders()
  }

  const handleProcess = async (doi: string) => {
    setProcessing(doi)
    try {
      const res = await papersApi.process(doi)
      if (res.data.success) {
        loadPapers()
      } else {
        alert(res.data.message)
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || '处理失败')
    } finally {
      setProcessing(null)
    }
  }

  const handleDelete = async (doi: string) => {
    if (!confirm('确定删除这篇论文？相关概念也会被删除。')) return
    try {
      await papersApi.delete(doi)
      loadPapers()
      loadFolders()
    } catch {
      alert('删除失败')
    }
  }

  const handleCreateFolder = async (name: string, description: string) => {
    try {
      await foldersApi.create({ name, description })
      loadFolders()
      setShowCreateFolder(false)
    } catch {
      alert('创建失败')
    }
  }

  const handleDeleteFolder = async (folderId: string) => {
    if (!confirm('确定删除此文件夹？论文将移到默认文件夹。')) return
    try {
      await foldersApi.delete(folderId)
      if (activeFolder === folderId) setActiveFolder('default')
      loadFolders()
      loadPapers()
    } catch {
      alert('删除失败')
    }
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      downloaded: 'bg-blue-100 text-blue-800',
      processed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    }
    return colors[status] || 'bg-gray-100 text-gray-800'
  }

  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds}秒`
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    if (minutes < 60) return `${minutes}分${secs > 0 ? secs + '秒' : ''}`
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return `${hours}小时${mins > 0 ? mins + '分' : ''}`
  }

  if (loading) {
    return <div className="text-center py-12">加载中...</div>
  }

  return (
    <div className="flex h-[calc(100vh-80px)]">
      {/* Folder Sidebar */}
      <div className={`bg-white border-r flex flex-col transition-all duration-300 ${sidebarCollapsed ? 'w-12' : 'w-64'}`}>
        {/* Collapse Toggle Button */}
        <div className="p-2 border-b flex justify-end">
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
            title={sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </button>
        </div>
        {!sidebarCollapsed && (
          <>
            <div className="px-4 py-2 border-b">
              <h2 className="font-semibold text-gray-700 text-sm">文件夹</h2>
            </div>
            <div className="flex-1 overflow-y-auto">
              {folders.map(folder => (
                <div
                  key={folder.id}
                  className={`flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-50 ${
                    activeFolder === folder.id ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-500' : 'text-gray-700'
                  }`}
                  onClick={() => setActiveFolder(folder.id)}
                >
                  <div className="flex items-center gap-2">
                    <Folder className="h-4 w-4" />
                    <span className="text-sm">{folder.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">{folder.paper_count}</span>
                    {folder.id !== 'default' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteFolder(folder.id) }}
                        className="text-gray-400 hover:text-red-500"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div className="p-4 border-t">
              <button
                onClick={() => setShowCreateFolder(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
              >
                <FolderPlus className="h-4 w-4" />
                新建文件夹
              </button>
            </div>
          </>
        )}
        {sidebarCollapsed && (
          <div className="flex-1 flex flex-col items-center py-2 gap-1">
            {folders.map(folder => (
              <button
                key={folder.id}
                onClick={() => { setActiveFolder(folder.id); setSidebarCollapsed(false) }}
                className={`p-2 rounded hover:bg-gray-100 ${activeFolder === folder.id ? 'bg-blue-100 text-blue-600' : 'text-gray-500'}`}
                title={folder.name}
              >
                <Folder className="h-4 w-4" />
              </button>
            ))}
            <button
              onClick={() => setShowCreateFolder(true)}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
              title="新建文件夹"
            >
              <FolderPlus className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold">论文管理</h1>
            <div className="flex gap-4">
              <button
                onClick={() => { loadPapers(); loadFolders(); }}
                className="flex items-center px-4 py-2 border rounded-lg hover:bg-gray-50"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                刷新
              </button>
              {papers.filter(p => p.status === 'pending').length > 0 && (
                <button
                  onClick={handleBatchProcess}
                  disabled={queueState.current !== null}
                  className="flex items-center px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
                >
                  {queueState.current !== null ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      处理中...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-2" />
                      批量处理 ({papers.filter(p => p.status === 'pending').length})
                    </>
                  )}
                </button>
              )}
              <label className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-lg cursor-pointer hover:bg-blue-600">
                <Upload className="h-4 w-4 mr-2" />
                {uploading ? '上传中...' : '上传 PDF'}
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
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-medium mb-3">上传结果</h3>
              <div className="space-y-2">
                {uploadResults.map((result, idx) => (
                  <div key={idx} className={`flex items-start p-2 rounded ${result.success ? 'bg-green-50' : 'bg-red-50'}`}>
                    {result.success ? (
                      <CheckCircle className="h-4 w-4 text-green-500 mr-2 mt-0.5" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500 mr-2 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <div className="font-medium">{result.filename}</div>
                      {result.success && result.title && (
                        <div className="text-sm text-gray-500">{result.title}</div>
                      )}
                      {result.message && (
                        <div className={`text-sm ${result.status === 'processed' ? 'text-green-600' : result.status === 'pending' ? 'text-yellow-600' : 'text-gray-500'}`}>
                          {result.message}
                        </div>
                      )}
                      {!result.success && result.error && (
                        <div className="text-sm text-red-500">{result.error}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Queue Progress */}
          {(queueState.current !== null || queueState.completed > 0) && (
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-medium mb-3">
                {queueState.current !== null ? '批量处理中...' : '批量处理完成'}
              </h3>
              <div className="flex items-center gap-4">
                <div className="flex-1 bg-gray-200 rounded-full h-2.5">
                  <div
                    className="bg-green-500 h-2.5 rounded-full transition-all"
                    style={{ width: `${(queueState.completed + queueState.pending.length) > 0 ? (queueState.completed / (queueState.completed + queueState.pending.length)) * 100 : 0}%` }}
                  />
                </div>
                <span className="text-sm text-gray-600">
                  {queueState.completed}/{queueState.completed + queueState.pending.length}
                </span>
              </div>
              <div className="flex gap-4 mt-2 text-sm">
                <span className="text-green-600">成功: {queueState.successful}</span>
                <span className="text-red-600">失败: {queueState.failed}</span>
                {queueState.estimatedTime > 0 && queueState.current !== null && (
                  <span className="text-gray-500">
                    预估剩余: {formatTime(queueState.estimatedTime)}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Paper Table */}
          {papers.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg shadow">
              <FileText className="h-12 w-12 mx-auto text-gray-400" />
              <p className="mt-4 text-gray-500">暂无论文，上传 PDF 开始</p>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">标题</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">节点数</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">根概念</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {papers.map(paper => (
                    <tr key={paper.doi} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-gray-900">{paper.title}</div>
                        {paper.authors && paper.authors.length > 0 && (
                          <div className="text-sm text-gray-500">
                            {Array.isArray(paper.authors) ? paper.authors.slice(0, 3).join(', ') : paper.authors}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 text-xs rounded-full ${getStatusBadge(paper.status)}`}>
                          {paper.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        <div className="flex items-center gap-1">
                          <GitBranch className="h-3 w-3" />
                          {paper.status === 'processed' ? (contributions[paper.doi]?.node_count || '-') : '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {paper.status === 'processed' ? (contributions[paper.doi]?.root_concept || '-') : '-'}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex justify-end gap-2">
                          {paper.status === 'pending' && (
                            <button
                              onClick={() => handleProcess(paper.doi)}
                              disabled={processing === paper.doi}
                              className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                              title="处理论文"
                            >
                              {processing === paper.doi ? (
                                <RefreshCw className="h-4 w-4 animate-spin" />
                              ) : (
                                <Play className="h-4 w-4" />
                              )}
                            </button>
                          )}
                          <button
                            onClick={() => handleDelete(paper.doi)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded"
                            title="删除"
                          >
                            <Trash2 className="h-4 w-4" />
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
  )
}