import { useEffect, useState, useRef } from 'react'
import { Upload, FileText, Trash2, Play, RefreshCw } from 'lucide-react'
import { papersApi } from '../lib/api'

interface Paper {
  doi: string
  title: string
  abstract: string | null
  authors: string[]
  status: string
  created_at: string
}

export default function Papers() {
  const [papers, setPapers] = useState<Paper[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [processing, setProcessing] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadPapers = () => {
    papersApi.list().then(res => {
      setPapers(res.data)
      setLoading(false)
    })
  }

  useEffect(() => {
    loadPapers()
  }, [])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      await papersApi.upload(file)
      loadPapers()
    } catch (err) {
      alert('上传失败')
    } finally {
      setUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
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
    if (!confirm('确定删除这篇论文？')) return
    try {
      await papersApi.delete(doi)
      loadPapers()
    } catch (err) {
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

  if (loading) {
    return <div className="text-center py-12">加载中...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">论文管理</h1>
        <div className="flex gap-4">
          <button
            onClick={() => loadPapers()}
            className="flex items-center px-4 py-2 border rounded-lg hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </button>
          <label className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-lg cursor-pointer hover:bg-blue-600">
            <Upload className="h-4 w-4 mr-2" />
            {uploading ? '上传中...' : '上传 PDF'}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={handleUpload}
              disabled={uploading}
            />
          </label>
        </div>
      </div>

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
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  标题
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  状态
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  创建时间
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {papers.map(paper => (
                <tr key={paper.doi} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">
                      {paper.title}
                    </div>
                    {paper.authors?.length > 0 && (
                      <div className="text-sm text-gray-500">
                        {paper.authors.slice(0, 3).join(', ')}
                        {paper.authors.length > 3 && '...'}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs rounded-full ${getStatusBadge(paper.status)}`}>
                      {paper.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {new Date(paper.created_at).toLocaleDateString()}
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
  )
}