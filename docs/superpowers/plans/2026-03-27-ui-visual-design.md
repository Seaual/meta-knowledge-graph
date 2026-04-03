# 微渐变极简视觉风格实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 改进整体视觉风格，使用品牌色点缀的极简设计，提升界面的精致感和层次感。

**Architecture:** 通过 Tailwind CSS 扩展品牌色变量，修改各组件的样式类名，实现渐变背景、精致阴影、品牌色边框等视觉效果。

**Tech Stack:** React, TypeScript, Tailwind CSS

---

## 文件结构

**修改文件：**
- `frontend/tailwind.config.js` - 添加品牌色变量
- `frontend/src/index.css` - 添加全局背景渐变
- `frontend/src/pages/Home.tsx` - 统计卡片和快速操作样式
- `frontend/src/pages/Papers.tsx` - 侧边栏和表格样式
- `frontend/src/pages/ConceptsGraph.tsx` - 顶部按钮和浮窗面板样式

---

## Task 1: 添加品牌色变量到 Tailwind 配置

**Files:**
- Modify: `frontend/tailwind.config.js`

- [ ] **Step 1: 更新 Tailwind 配置**

将 `frontend/tailwind.config.js` 替换为：

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
        },
      },
      boxShadow: {
        'brand': '0 2px 8px rgba(99, 102, 241, 0.08)',
        'brand-lg': '0 4px 12px rgba(99, 102, 241, 0.1)',
        'brand-xl': '0 8px 24px rgba(99, 102, 241, 0.12)',
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 2: 验证配置语法**

```bash
cd D:/meta-knowledge-graph-main/frontend && npm run build
```

Expected: Build successful

- [ ] **Step 3: 提交**

```bash
git add frontend/tailwind.config.js
git commit -m "feat(design): add brand colors to Tailwind config"
```

---

## Task 2: 添加全局背景渐变样式

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: 更新全局样式**

将 `frontend/src/index.css` 替换为：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
}

body {
  margin: 0;
  min-height: 100vh;
  /* 渐变背景 */
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
}

/* React Flow styles */
.react-flow__node {
  cursor: pointer;
}

.react-flow__edge-path {
  stroke-width: 2;
}

.react-flow__controls {
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

.react-flow__controls-button {
  border: none;
  background: white;
}

.react-flow__controls-button:hover {
  background: #f3f4f6;
}

.react-flow__background {
  background-color: #f8fafc;
}

/* 品牌色渐变背景卡片 */
.bg-brand-gradient {
  background: linear-gradient(135deg, #ffffff 0%, #fafbfc 100%);
}

/* 品牌色填充渐变 */
.bg-brand-fill {
  background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%);
}

/* 品牌色按钮渐变 */
.bg-brand-button {
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
}

/* 品牌色边框 */
.border-brand {
  border-color: rgba(99, 102, 241, 0.1);
}
```

- [ ] **Step 2: 验证样式编译**

```bash
cd D:/meta-knowledge-graph-main/frontend && npm run build
```

Expected: Build successful

- [ ] **Step 3: 提交**

```bash
git add frontend/src/index.css
git commit -m "feat(design): add global gradient background and brand utility classes"
```

---

## Task 3: 改进首页统计卡片样式

**Files:**
- Modify: `frontend/src/pages/Home.tsx`

- [ ] **Step 1: 更新统计卡片样式**

找到 Home.tsx 中的统计卡片部分（约第 50-90 行），将整个 stats grid 替换为：

```tsx
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-brand-gradient rounded-2xl shadow-brand p-6 border border-brand">
          <div className="flex items-center">
            <div className="h-11 w-11 bg-brand-button rounded-xl flex items-center justify-center">
              <FileText className="h-5 w-5 text-white" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-brand-500 font-medium">论文总数</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.papers?.total || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-brand-gradient rounded-2xl shadow-brand p-6 border border-brand">
          <div className="flex items-center">
            <div className="h-11 w-11 bg-brand-button rounded-xl flex items-center justify-center">
              <GitBranch className="h-5 w-5 text-white" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-brand-500 font-medium">概念总数</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.concepts?.total || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-brand-gradient rounded-2xl shadow-brand p-6 border border-brand">
          <div className="flex items-center">
            <div className="h-11 w-11 bg-brand-button rounded-xl flex items-center justify-center">
              <Network className="h-5 w-5 text-white" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-brand-500 font-medium">层级关系</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.relations || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-brand-gradient rounded-2xl shadow-brand p-6 border border-brand">
          <div className="flex items-center">
            <div className="h-11 w-11 bg-brand-button rounded-xl flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-white" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-brand-500 font-medium">根概念</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.root_concepts || 0}</p>
            </div>
          </div>
        </div>
      </div>
```

- [ ] **Step 2: 验证编译**

```bash
cd D:/meta-knowledge-graph-main/frontend && npm run build
```

Expected: Build successful

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/Home.tsx
git commit -m "feat(design): improve home page stats cards with brand colors"
```

---

## Task 4: 改进首页快速操作样式

**Files:**
- Modify: `frontend/src/pages/Home.tsx`

- [ ] **Step 1: 更新快速操作卡片样式**

找到 Home.tsx 中的快速操作部分（约第 93-130 行），将整个 Quick Actions 区域替换为：

```tsx
      {/* Quick Actions */}
      <div className="bg-brand-gradient rounded-2xl shadow-brand p-6 border border-brand">
        <h2 className="text-lg font-semibold mb-4 text-brand-600">快速操作</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/papers"
            className="flex items-center p-4 bg-brand-fill rounded-xl hover:shadow-brand transition-all"
          >
            <div className="h-10 w-10 bg-brand-button rounded-lg flex items-center justify-center mr-3">
              <FileText className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-medium text-brand-700">上传论文</p>
              <p className="text-sm text-brand-500">上传 PDF 并提取概念</p>
            </div>
          </Link>

          <Link
            to="/concepts"
            className="flex items-center p-4 bg-brand-fill rounded-xl hover:shadow-brand transition-all"
          >
            <div className="h-10 w-10 bg-brand-button rounded-lg flex items-center justify-center mr-3">
              <GitBranch className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-medium text-brand-700">浏览概念</p>
              <p className="text-sm text-brand-500">查看概念层级树</p>
            </div>
          </Link>

          <button
            onClick={() => setShowLLMModal(true)}
            className="flex items-center p-4 bg-brand-fill rounded-xl hover:shadow-brand transition-all text-left"
          >
            <div className="h-10 w-10 bg-brand-button rounded-lg flex items-center justify-center mr-3">
              <Settings className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-medium text-brand-700">LLM 配置</p>
              <p className="text-sm text-brand-500">{llmStatus || '配置 AI 服务商'}</p>
            </div>
          </button>
        </div>
      </div>
```

- [ ] **Step 2: 更新论文状态卡片样式**

找到论文状态部分（约第 147-160 行），替换为：

```tsx
      {/* Paper Status */}
      {stats?.papers && (
        <div className="bg-brand-gradient rounded-2xl shadow-brand p-6 border border-brand">
          <h2 className="text-lg font-semibold mb-4 text-brand-600">论文状态</h2>
          <div className="flex gap-6">
            {Object.entries(stats.papers).filter(([k]) => k !== 'total').map(([status, count]) => (
              <div key={status} className="text-center p-4 bg-brand-fill rounded-xl">
                <p className="text-2xl font-bold text-brand-700">{count}</p>
                <p className="text-sm text-brand-500">{status}</p>
              </div>
            ))}
          </div>
        </div>
      )}
```

- [ ] **Step 3: 验证编译**

```bash
cd D:/meta-knowledge-graph-main/frontend && npm run build
```

Expected: Build successful

- [ ] **Step 4: 提交**

```bash
git add frontend/src/pages/Home.tsx
git commit -m "feat(design): improve home page quick actions with gradient cards"
```

---

## Task 5: 改进论文页侧边栏展开状态样式

**Files:**
- Modify: `frontend/src/pages/Papers.tsx`

- [ ] **Step 1: 更新侧边栏容器样式**

找到 Papers.tsx 中侧边栏部分（约第 341-421 行），将整个侧边栏 div 替换为：

```tsx
      {/* Folder Sidebar */}
      <div className={`bg-brand-gradient flex flex-col transition-all duration-300 border-r border-brand ${sidebarCollapsed ? 'w-12' : 'w-64'}`}>
        {/* Collapse Toggle Button */}
        <div className="p-2 border-b border-brand flex justify-end">
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-1.5 text-brand-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg"
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
            <div className="px-4 py-3 border-b border-brand">
              <h2 className="font-semibold text-brand-600 text-sm flex items-center gap-2">
                <Folder className="h-4 w-4" />
                文件夹
              </h2>
            </div>
            <div className="flex-1 overflow-y-auto py-2">
              {folders.map(folder => (
                <div
                  key={folder.id}
                  className={`flex items-center justify-between px-4 py-3 cursor-pointer transition-all ${
                    activeFolder === folder.id
                      ? 'bg-brand-fill text-brand-700 border-r-2 border-brand-600 mx-2 rounded-xl'
                      : 'text-gray-700 hover:bg-gray-50 mx-2 rounded-xl'
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
            <div className="p-4 border-t border-brand">
              <button
                onClick={() => setShowCreateFolder(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border-2 border-dashed border-brand-300 rounded-xl text-sm text-brand-600 hover:bg-brand-50 transition-all"
              >
                <FolderPlus className="h-4 w-4" />
                新建文件夹
              </button>
            </div>
          </>
        )}
        {sidebarCollapsed && (
          <div className="flex-1 flex flex-col items-center py-2 gap-1">
            <button
              onClick={() => setSidebarCollapsed(false)}
              className="p-2 text-brand-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg mb-2"
              title="展开侧边栏"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
            {folders.map(folder => (
              <button
                key={folder.id}
                onClick={() => { setActiveFolder(folder.id); setSidebarCollapsed(false) }}
                className={`p-2 rounded-lg transition-all ${activeFolder === folder.id ? 'bg-brand-fill text-brand-600' : 'text-gray-500 hover:bg-gray-100'}`}
                title={folder.name}
              >
                <Folder className="h-4 w-4" />
              </button>
            ))}
            <button
              onClick={() => setShowCreateFolder(true)}
              className="p-2 text-brand-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg mt-2"
              title="新建文件夹"
            >
              <FolderPlus className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
```

- [ ] **Step 2: 验证编译**

```bash
cd D:/meta-knowledge-graph-main/frontend && npm run build
```

Expected: Build successful

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/Papers.tsx
git commit -m "feat(design): improve papers page sidebar with brand styling"
```

---

## Task 6: 改进论文页表格样式

**Files:**
- Modify: `frontend/src/pages/Papers.tsx`

- [ ] **Step 1: 更新表格容器样式**

找到 Papers.tsx 中表格部分（约第 534-606 行），将表格区域替换为：

```tsx
          {/* Paper Table */}
          {papers.length === 0 ? (
            <div className="text-center py-12 bg-brand-gradient rounded-2xl shadow-brand border border-brand">
              <FileText className="h-12 w-12 mx-auto text-brand-300" />
              <p className="mt-4 text-brand-500">暂无论文，上传 PDF 开始</p>
            </div>
          ) : (
            <div className="bg-brand-gradient rounded-2xl shadow-brand border border-brand overflow-hidden">
              <table className="min-w-full divide-y divide-brand-100">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-brand-600 uppercase tracking-wider">标题</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-brand-600 uppercase tracking-wider">状态</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-brand-600 uppercase tracking-wider">节点数</th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-brand-600 uppercase tracking-wider">根概念</th>
                    <th className="px-6 py-4 text-right text-xs font-semibold text-brand-600 uppercase tracking-wider">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-50">
                  {papers.map(paper => (
                    <tr key={paper.doi} className="hover:bg-brand-50/50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-gray-900">{paper.title}</div>
                        {paper.authors && paper.authors.length > 0 && (
                          <div className="text-sm text-gray-500">
                            {Array.isArray(paper.authors) ? paper.authors.slice(0, 3).join(', ') : paper.authors}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-3 py-1 text-xs rounded-full font-medium ${getStatusBadge(paper.status)}`}>
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
                              className="p-2 text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
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
                            className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
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
```

- [ ] **Step 2: 更新状态标签样式函数**

找到 `getStatusBadge` 函数（约第 315-323 行），替换为：

```tsx
  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-amber-100 text-amber-700',
      downloaded: 'bg-blue-100 text-blue-700',
      processed: 'bg-emerald-100 text-emerald-700',
      failed: 'bg-red-100 text-red-700',
    }
    return colors[status] || 'bg-gray-100 text-gray-700'
  }
```

- [ ] **Step 3: 更新上传结果和队列进度卡片样式**

找到上传结果部分（约第 473-502 行），替换为：

```tsx
          {/* Upload Results */}
          {uploadResults.length > 0 && (
            <div className="bg-brand-gradient rounded-2xl shadow-brand p-4 border border-brand">
              <h3 className="font-medium mb-3 text-brand-600">上传结果</h3>
              <div className="space-y-2">
                {uploadResults.map((result, idx) => (
                  <div key={idx} className={`flex items-start p-3 rounded-xl ${result.success ? 'bg-emerald-50' : 'bg-red-50'}`}>
                    {result.success ? (
                      <CheckCircle className="h-4 w-4 text-emerald-500 mr-2 mt-0.5" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500 mr-2 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <div className="font-medium">{result.filename}</div>
                      {result.success && result.title && (
                        <div className="text-sm text-gray-500">{result.title}</div>
                      )}
                      {result.message && (
                        <div className={`text-sm ${result.status === 'processed' ? 'text-emerald-600' : result.status === 'pending' ? 'text-amber-600' : 'text-gray-500'}`}>
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
```

找到队列进度部分（约第 505-531 行），替换为：

```tsx
          {/* Queue Progress */}
          {(queueState.current !== null || queueState.completed > 0) && (
            <div className="bg-brand-gradient rounded-2xl shadow-brand p-4 border border-brand">
              <h3 className="font-medium mb-3 text-brand-600">
                {queueState.current !== null ? '批量处理中...' : '批量处理完成'}
              </h3>
              <div className="flex items-center gap-4">
                <div className="flex-1 bg-gray-200 rounded-full h-2.5">
                  <div
                    className="bg-brand-button h-2.5 rounded-full transition-all"
                    style={{ width: `${(queueState.completed + queueState.pending.length) > 0 ? (queueState.completed / (queueState.completed + queueState.pending.length)) * 100 : 0}%` }}
                  />
                </div>
                <span className="text-sm text-gray-600 font-medium">
                  {queueState.completed}/{queueState.completed + queueState.pending.length}
                </span>
              </div>
              <div className="flex gap-4 mt-2 text-sm">
                <span className="text-emerald-600">成功: {queueState.successful}</span>
                <span className="text-red-600">失败: {queueState.failed}</span>
                {queueState.estimatedTime > 0 && queueState.current !== null && (
                  <span className="text-gray-500">
                    预估剩余: {formatTime(queueState.estimatedTime)}
                  </span>
                )}
              </div>
            </div>
          )}
```

- [ ] **Step 4: 更新顶部操作按钮样式**

找到顶部操作按钮部分（约第 427-469 行），替换为：

```tsx
          {/* Header */}
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-900">论文管理</h1>
            <div className="flex gap-3">
              <button
                onClick={() => { loadPapers(); loadFolders(); }}
                className="flex items-center px-4 py-2.5 bg-brand-gradient border border-brand rounded-xl hover:shadow-brand text-gray-700 transition-all"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                刷新
              </button>
              {papers.filter(p => p.status === 'pending').length > 0 && (
                <button
                  onClick={handleBatchProcess}
                  disabled={queueState.current !== null}
                  className="flex items-center px-4 py-2.5 bg-brand-button text-white rounded-xl hover:shadow-brand-lg disabled:opacity-50 transition-all"
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
              <label className="flex items-center px-4 py-2.5 bg-brand-button text-white rounded-xl cursor-pointer hover:shadow-brand-lg transition-all">
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
```

- [ ] **Step 5: 验证编译**

```bash
cd D:/meta-knowledge-graph-main/frontend && npm run build
```

Expected: Build successful

- [ ] **Step 6: 提交**

```bash
git add frontend/src/pages/Papers.tsx
git commit -m "feat(design): improve papers page table and buttons with brand styling"
```

---

## Task 7: 改进图谱页顶部按钮样式

**Files:**
- Modify: `frontend/src/pages/ConceptsGraph.tsx`

- [ ] **Step 1: 更新顶部按钮区域样式**

找到 ConceptsGraph.tsx 中 Action Buttons 部分（约第 576-660 行），将整个区域替换为：

```tsx
      {/* Action Buttons */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        {/* Folder Selector */}
        <div className="relative">
          <button
            onClick={() => setShowFolderMenu(!showFolderMenu)}
            className="flex items-center gap-2 px-4 py-2.5 bg-brand-gradient backdrop-blur rounded-xl shadow-brand text-sm font-medium text-brand-600 hover:shadow-brand-lg border border-brand transition-all"
          >
            <Folder className="h-4 w-4" />
            {folders.find(f => f.id === activeFolder)?.name || '默认'}
            <ChevronDown className="h-4 w-4" />
          </button>
          {showFolderMenu && (
            <div className="absolute right-0 mt-2 w-48 bg-brand-gradient rounded-xl shadow-brand-lg border border-brand overflow-hidden z-20">
              {folders.map(folder => (
                <button
                  key={folder.id}
                  onClick={() => {
                    setActiveFolder(folder.id)
                    setShowFolderMenu(false)
                  }}
                  className={`w-full text-left px-4 py-2.5 text-sm hover:bg-brand-fill flex items-center gap-2 transition-colors ${
                    activeFolder === folder.id ? 'bg-brand-fill text-brand-700' : 'text-gray-700'
                  }`}
                >
                  <Folder className="h-4 w-4" />
                  {folder.name}
                </button>
              ))}
            </div>
          )}
        </div>
        {/* Export Dropdown - only show in 'all' view */}
        {viewMode === 'all' && (
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              className="flex items-center gap-2 px-4 py-2.5 bg-brand-gradient backdrop-blur rounded-xl shadow-brand text-sm font-medium text-brand-600 hover:shadow-brand-lg border border-brand transition-all"
            >
              <Download className="h-4 w-4" />
              导出
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {showExportMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-brand-gradient rounded-xl shadow-brand-lg border border-brand overflow-hidden z-20">
                <button
                  onClick={() => { handleExportHtml(); setShowExportMenu(false); }}
                  className="w-full px-4 py-3 text-left text-sm text-gray-700 hover:bg-brand-fill flex items-center gap-3 transition-colors"
                >
                  <span className="text-lg">🌐</span>
                  <div>
                    <div className="font-medium">HTML 页面</div>
                    <div className="text-xs text-gray-400">交互式物理渲染</div>
                  </div>
                </button>
                <button
                  onClick={() => { handleExportCanvas(); setShowExportMenu(false); }}
                  className="w-full px-4 py-3 text-left text-sm text-gray-700 hover:bg-brand-fill flex items-center gap-3 transition-colors"
                >
                  <span className="text-lg">🎨</span>
                  <div>
                    <div className="font-medium">Canvas 格式</div>
                    <div className="text-xs text-gray-400">带颜色和布局</div>
                  </div>
                </button>
                <button
                  onClick={() => { handleExportMarkdown(); setShowExportMenu(false); }}
                  className="w-full px-4 py-3 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3 transition-colors"
                >
                  <span className="text-lg">📝</span>
                  <div>
                    <div className="font-medium">Markdown 格式</div>
                    <div className="text-xs text-gray-400">纯文本双链</div>
                  </div>
                </button>
              </div>
            )}
          </div>
        )}
        {viewMode === 'all' && (
          <button
            onClick={() => setDedupOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-brand-button backdrop-blur rounded-xl shadow-brand text-sm font-medium text-white hover:shadow-brand-lg transition-all"
          >
            🔄 去重扫描
          </button>
        )}
      </div>
```

- [ ] **Step 2: 更新返回按钮样式**

找到 Top Bar 部分（约第 564-573 行），替换为：

```tsx
      {/* Top Bar */}
      <div className="absolute top-4 left-4 z-10">
        {viewMode === 'concept' && (
          <button
            onClick={handleBack}
            className="flex items-center gap-2 px-4 py-2.5 bg-brand-gradient backdrop-blur rounded-xl shadow-brand text-sm font-medium text-brand-600 hover:shadow-brand-lg border border-brand transition-all"
          >
            ← 返回全部概念
          </button>
        )}
      </div>
```

- [ ] **Step 3: 验证编译**

```bash
cd D:/meta-knowledge-graph-main/frontend && npm run build
```

Expected: Build successful

- [ ] **Step 4: 提交**

```bash
git add frontend/src/pages/ConceptsGraph.tsx
git commit -m "feat(design): improve graph page top buttons with brand styling"
```

---

## Task 8: 改进图谱页浮窗面板样式

**Files:**
- Modify: `frontend/src/pages/ConceptsGraph.tsx`

- [ ] **Step 1: 更新左下角信息面板样式**

找到 Info Panel 部分（约第 663-695 行），替换为：

```tsx
      {/* Info Panel */}
      <div className="absolute bottom-16 left-4 bg-brand-gradient backdrop-blur rounded-2xl shadow-brand p-4 z-10 border border-brand">
        <div className="text-xs text-brand-500 font-medium">
          {viewMode === 'all' ? '知识图谱' : '概念详情'}
        </div>
        <div className="font-bold text-gray-900 text-lg">
          {viewMode === 'all' ? `${concepts.length} 个概念` : selectedConcept?.text}
        </div>
        <div className="text-xs text-gray-500 mt-1">
          {viewMode === 'all'
            ? '点击概念查看操作'
            : '点击论文查看详情'
          }
        </div>
        {/* Force Strength Slider */}
        <div className="mt-3 pt-3 border-t border-brand-200">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-500">节点斥力</span>
            <span className="text-xs font-medium text-brand-600">{forceStrength}</span>
          </div>
          <input
            type="range"
            min="50"
            max="400"
            value={forceStrength}
            onChange={(e) => setForceStrength(Number(e.target.value))}
            className="w-full h-1.5 bg-brand-100 rounded-lg appearance-none cursor-pointer accent-brand-600"
          />
          <div className="flex justify-between text-[10px] text-gray-400 mt-1">
            <span>紧凑</span>
            <span>分散</span>
          </div>
        </div>
      </div>
```

- [ ] **Step 2: 更新右下角图例样式**

找到 Legend 部分（约第 999-1015 行），替换为：

```tsx
      {/* Legend */}
      <div className="absolute bottom-16 right-4 bg-brand-gradient backdrop-blur rounded-2xl shadow-brand p-4 z-10 border border-brand">
        <div className="text-xs font-semibold text-brand-600 mb-2">图例</div>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-gradient-to-br from-red-400 to-red-500" />
            <span className="text-xs text-gray-600">概念节点</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-gradient-to-br from-blue-400 to-blue-500" />
            <span className="text-xs text-gray-600">论文节点</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-gradient-to-br from-purple-400 to-purple-500" />
            <span className="text-xs text-gray-600">中心概念</span>
          </div>
        </div>
      </div>
```

- [ ] **Step 3: 更新概念操作面板样式**

找到 Concept Action Panel 部分（约第 698-745 行），替换为：

```tsx
      {/* Concept Action Panel - 点击概念后显示 */}
      {showConceptActions && selectedConcept && (
        <div className="absolute top-4 right-4 bg-brand-gradient rounded-2xl shadow-brand-lg p-4 z-20 w-72 border border-brand">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="font-bold text-gray-900 text-sm">{selectedConcept.text}</h3>
              <div className="flex items-center gap-2 mt-1">
                {selectedConcept.category && (
                  <span
                    className="px-2 py-0.5 rounded-full text-xs font-medium"
                    style={{
                      backgroundColor: CATEGORY_COLORS[selectedConcept.category] + '20',
                      color: CATEGORY_COLORS[selectedConcept.category],
                    }}
                  >
                    {selectedConcept.category}
                  </span>
                )}
                <span className="text-xs text-gray-500">{selectedConcept.paper_count || 0} 篇论文</span>
              </div>
            </div>
            <button
              onClick={() => {
                setShowConceptActions(false)
                setSelectedConcept(null)
              }}
              className="text-gray-400 hover:text-brand-600 transition-colors"
            >
              ✕
            </button>
          </div>
          <div className="space-y-2">
            <button
              onClick={handleDiscoverResearchPoints}
              className="w-full px-4 py-2.5 bg-brand-button text-white text-sm font-medium rounded-xl hover:shadow-brand transition-all flex items-center justify-center gap-2"
            >
              🔍 发现研究点
            </button>
            {selectedConcept.papers && selectedConcept.papers.length > 0 && (
              <button
                onClick={handleViewPapers}
                className="w-full px-4 py-2.5 bg-brand-fill text-brand-700 text-sm font-medium rounded-xl hover:shadow-brand transition-all flex items-center justify-center gap-2"
              >
                📄 查看相关论文 ({selectedConcept.papers.length})
              </button>
            )}
          </div>
        </div>
      )}
```

- [ ] **Step 4: 更新悬浮提示样式**

找到 Hover Tooltip 部分（约第 748-784 行），替换为：

```tsx
      {/* Hover Tooltip - 简单显示 */}
      {hoverNode && !showConceptActions && (
        <div className="absolute top-4 right-4 bg-brand-gradient backdrop-blur rounded-2xl shadow-brand p-3 z-10 max-w-xs pointer-events-none border border-brand">
          <div className="font-semibold text-gray-900 text-sm">
            {hoverNode.name}
          </div>
          <div className="flex items-center gap-2 mt-1">
            {hoverNode.type === 'paper' ? (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-600">
                论文
              </span>
            ) : hoverNode.type === 'center' ? (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-600">
                中心概念
              </span>
            ) : (
              <>
                <span
                  className="px-2 py-0.5 rounded-full text-xs font-medium"
                  style={{
                    backgroundColor: CATEGORY_COLORS[hoverNode.category || 'method'] + '20',
                    color: CATEGORY_COLORS[hoverNode.category || 'method'],
                  }}
                >
                  {hoverNode.category}
                </span>
                <span className="text-xs text-gray-500">L{hoverNode.depth}</span>
              </>
            )}
          </div>
          {hoverNode.type === 'concept' && (
            <div className="text-xs text-gray-400 mt-1">点击查看操作</div>
          )}
          {hoverNode.type === 'paper' && (
            <div className="text-xs text-gray-400 mt-1">点击查看详情</div>
          )}
        </div>
      )}
```

- [ ] **Step 5: 更新论文详情面板样式**

找到 Paper Detail Panel 部分（约第 787-866 行），替换为：

```tsx
      {/* Paper Detail Panel */}
      {selectedPaper && (
        <div className="absolute bottom-20 right-4 w-96 bg-brand-gradient rounded-2xl shadow-brand-lg z-20 max-h-[70vh] overflow-y-auto border border-brand">
          <div className="p-4 border-b border-brand sticky top-0 bg-brand-gradient">
            <div className="flex items-start justify-between">
              <h3 className="font-bold text-gray-900 text-sm leading-tight pr-2">
                {selectedPaper.title}
              </h3>
              <button
                onClick={() => setSelectedPaper(null)}
                className="text-gray-400 hover:text-brand-600 transition-colors flex-shrink-0"
              >
                ✕
              </button>
            </div>
          </div>

          <div className="p-4 space-y-4">
            {/* DOI */}
            <div>
              <div className="text-xs font-semibold text-brand-500 mb-1">DOI</div>
              <div className="text-xs text-blue-500 break-all">{selectedPaper.doi}</div>
            </div>

            {/* Authors */}
            {selectedPaper.authors && selectedPaper.authors.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-brand-500 mb-1">作者</div>
                <div className="text-sm text-gray-700">
                  {selectedPaper.authors.slice(0, 5).join(', ')}
                  {selectedPaper.authors.length > 5 && (
                    <span className="text-gray-400"> +{selectedPaper.authors.length - 5} 人</span>
                  )}
                </div>
              </div>
            )}

            {/* Keywords */}
            {selectedPaper.keywords && selectedPaper.keywords.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-brand-500 mb-2">关键词</div>
                <div className="flex flex-wrap gap-1">
                  {selectedPaper.keywords.map((kw, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 bg-brand-fill text-brand-700 rounded-full text-xs"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Abstract */}
            {selectedPaper.abstract && (
              <div>
                <div className="text-xs font-semibold text-brand-500 mb-1">摘要</div>
                <div className="text-sm text-gray-600 leading-relaxed">
                  {selectedPaper.abstract}
                </div>
              </div>
            )}

            {/* Contributions */}
            {selectedPaper.contributions && selectedPaper.contributions.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-brand-500 mb-2">主要贡献</div>
                <ul className="text-sm text-gray-600 space-y-1">
                  {selectedPaper.contributions.slice(0, 3).map((c, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-brand-500 mt-1">•</span>
                      <span>{c}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
```

- [ ] **Step 6: 更新研究点面板样式**

找到 Research Points Panel 部分（约第 869-996 行），替换为：

```tsx
      {/* Research Points Panel */}
      {showResearchPanel && (
        <div className="absolute top-20 left-4 w-[480px] bg-brand-gradient rounded-2xl shadow-brand-lg z-20 max-h-[75vh] overflow-y-auto border border-brand">
          <div className="p-4 border-b border-brand sticky top-0 bg-brand-gradient">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-bold text-gray-900 text-base">🔍 研究点发现</h3>
                <p className="text-xs text-gray-500 mt-1">
                  基于「{researchPoints?.concept_name || selectedConcept?.text}」的分析
                </p>
              </div>
              <button
                onClick={() => setShowResearchPanel(false)}
                className="text-gray-400 hover:text-brand-600 transition-colors flex-shrink-0"
              >
                ✕
              </button>
            </div>
          </div>

          <div className="p-4 space-y-4">
            {loadingResearchPoints ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-4 border-brand-500 border-t-transparent mx-auto" />
                  <p className="mt-3 text-sm text-gray-500">正在分析知识图谱...</p>
                  <p className="text-xs text-gray-400 mt-1">追溯上游节点，遍历边缘节点</p>
                </div>
              </div>
            ) : researchPoints ? (
              <>
                {/* Analysis Context Summary */}
                <div className="bg-brand-fill rounded-xl p-3">
                  <div className="text-xs font-semibold text-brand-600 mb-2">分析上下文</div>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div>
                      <div className="text-lg font-bold text-brand-600">{researchPoints.analysis_context.ancestors.length}</div>
                      <div className="text-xs text-gray-500">上游节点</div>
                    </div>
                    <div>
                      <div className="text-lg font-bold text-brand-600">{researchPoints.analysis_context.descendants.length}</div>
                      <div className="text-xs text-gray-500">下游节点</div>
                    </div>
                    <div>
                      <div className="text-lg font-bold text-brand-600">{researchPoints.analysis_context.edge_nodes.length}</div>
                      <div className="text-xs text-gray-500">边缘节点</div>
                    </div>
                  </div>
                </div>

                {/* Research Points */}
                <div className="space-y-3">
                  {researchPoints.research_points.map((point, i) => (
                    <div key={i} className="border border-brand-100 rounded-xl p-3 hover:border-brand-300 hover:bg-brand-50/50 transition-colors">
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="font-semibold text-gray-900 text-sm">{point.title}</h4>
                        <div className="flex gap-1 flex-shrink-0">
                          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                            point.difficulty === 'low' ? 'bg-emerald-100 text-emerald-600' :
                            point.difficulty === 'medium' ? 'bg-amber-100 text-amber-600' :
                            point.difficulty === 'high' ? 'bg-red-100 text-red-600' :
                            'bg-gray-100 text-gray-500'
                          }`}>
                            {point.difficulty === 'low' ? '易' :
                             point.difficulty === 'medium' ? '中' :
                             point.difficulty === 'high' ? '难' : '?'}
                          </span>
                          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                            point.novelty === 'high' ? 'bg-orange-100 text-orange-600' :
                            point.novelty === 'moderate' ? 'bg-blue-100 text-blue-600' :
                            point.novelty === 'incremental' ? 'bg-gray-100 text-gray-500' :
                            'bg-gray-100 text-gray-500'
                          }`} title="创新性">
                            {point.novelty === 'high' ? '高创新' :
                             point.novelty === 'moderate' ? '中创新' :
                             point.novelty === 'incremental' ? '渐进' : '?'}
                          </span>
                          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                            point.potential_impact === 'transformative' ? 'bg-purple-100 text-purple-600' :
                            point.potential_impact === 'broad' ? 'bg-blue-100 text-blue-600' :
                            point.potential_impact === 'niche' ? 'bg-gray-100 text-gray-500' :
                            'bg-gray-100 text-gray-500'
                          }`} title="潜在影响">
                            {point.potential_impact === 'transformative' ? '变革性' :
                             point.potential_impact === 'broad' ? '广泛' :
                             point.potential_impact === 'niche' ? '特定' : '?'}
                          </span>
                        </div>
                      </div>
                      {point.hypothesis && (
                        <div className="mt-2 p-2 bg-blue-50 rounded-lg text-xs text-blue-700 italic">
                          💡 {point.hypothesis}
                        </div>
                      )}
                      <p className="text-sm text-gray-600 mt-2 leading-relaxed">{point.description}</p>
                      <div className="mt-2">
                        <div className="text-xs text-gray-400 mb-1">发现方法 · 研究价值</div>
                        <p className="text-xs text-gray-500">
                          {point.discovery_method === 'gap_filling' ? '🔍 空白地带法' :
                           point.discovery_method === 'leaf_extension' ? '🌱 末端延伸法' :
                           point.discovery_method === 'bottleneck' ? '🔥 瓶颈识别法' :
                           point.discovery_method === 'transfer' ? '🔄 迁移应用法' : ''} · {point.rationale}
                        </p>
                      </div>
                      {point.difficulty_reason && (
                        <div className="mt-1 text-xs text-gray-400">
                          难度依据: {point.difficulty_reason}
                        </div>
                      )}
                      {point.related_concepts && point.related_concepts.length > 0 && (
                        <div className="mt-2">
                          <div className="text-xs text-gray-400 mb-1">相关概念</div>
                          <div className="flex flex-wrap gap-1">
                            {point.related_concepts.slice(0, 5).map((c, j) => (
                              <span key={j} className="px-2 py-0.5 bg-brand-fill text-brand-700 rounded-full text-xs">
                                {c}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}
```

- [ ] **Step 7: 验证编译**

```bash
cd D:/meta-knowledge-graph-main/frontend && npm run build
```

Expected: Build successful

- [ ] **Step 8: 提交**

```bash
git add frontend/src/pages/ConceptsGraph.tsx
git commit -m "feat(design): improve graph page panels with brand styling"
```

---

## Task 9: 最终验证和构建

**Files:**
- All modified files

- [ ] **Step 1: 运行完整构建**

```bash
cd D:/meta-knowledge-graph-main/frontend && npm run build
```

Expected: Build successful without errors

- [ ] **Step 2: 本地测试**

```bash
cd D:/meta-knowledge-graph-main && python -m uvicorn backend.main:app --reload --port 8000
```

在另一个终端：
```bash
cd D:/meta-knowledge-graph-main/frontend && npm run dev
```

打开 http://localhost:5173 验证：
1. 首页统计卡片和快速操作样式
2. 论文页侧边栏展开/折叠状态
3. 图谱页顶部按钮和浮窗面板

- [ ] **Step 3: 最终提交**

```bash
git add -A
git commit -m "feat(design): complete gradient minimal visual style implementation"
```

---

## 成功标准

- [ ] 所有页面背景使用渐变
- [ ] 统计卡片圆角 16px，带品牌色边框
- [ ] 快速操作使用渐变填充卡片
- [ ] 论文页侧边栏展开/折叠状态样式正确
- [ ] 表格圆角 16px，状态标签胶囊化
- [ ] 图谱页顶部按钮渐变样式
- [ ] 浮窗面板圆角 14-16px，品牌色边框