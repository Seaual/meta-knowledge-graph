# Frontend API 模块化设计

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:writing-plans to create implementation plan after spec approval.

**Goal:** 将 `lib/api.ts` (675行) 拆分为按领域组织的小模块，提高可维护性。

**Architecture:** 每个 API 领域一个文件，类型定义与 API 方法在同一文件，`index.ts` 重新导出保持向后兼容。

**Tech Stack:** TypeScript, Axios, React

---

## 当前问题

`frontend/src/lib/api.ts` 包含 14 个 API 模块，共 675 行：
- papersApi, conceptsApi, graphApi, dedupApi
- batchApi, exportApi, llmApi, s2Api
- recommendationApi, s2PaperApi, citationApi
- foldersApi, agentApi, conversationsApi

问题：
- 单文件过大，难以维护
- 类型定义与方法混杂
- 难以单独测试

---

## 目标结构

```
frontend/src/lib/api/
├── index.ts          # 重新导出所有模块
├── client.ts         # axios 实例 + 拦截器 + deviceId
├── papers.ts         # papersApi + 类型
├── concepts.ts       # conceptsApi + 类型
├── graph.ts          # graphApi + 类型
├── dedup.ts          # dedupApi + 类型
├── batch.ts          # batchApi + 类型
├── export.ts         # exportApi + 类型
├── llm.ts            # llmApi + 类型
├── s2.ts             # s2Api + recommendationApi + s2PaperApi + 类型
├── citation.ts       # citationApi + 类型
├── folders.ts        # foldersApi + 类型
├── agent.ts          # agentApi + 类型
└── conversations.ts  # conversationsApi + 类型
```

---

## 模块详细设计

### client.ts

```typescript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Device ID management
const DEVICE_ID_KEY = 'mkg_device_id'

function getOrCreateDeviceId(): string {
  let deviceId = localStorage.getItem(DEVICE_ID_KEY)
  if (!deviceId) {
    deviceId = crypto.randomUUID()
    localStorage.setItem(DEVICE_ID_KEY, deviceId)
  }
  return deviceId
}

api.interceptors.request.use((config) => {
  config.headers['X-Device-ID'] = getOrCreateDeviceId()
  return config
})

export default api
export { getOrCreateDeviceId }
```

### papers.ts

包含：
- `papersApi` 对象 (list, get, upload, process, delete, move, contribution, processSingle)
- 类型：`PaperContribution`, `ProcessSingleResponse`

### concepts.ts

包含：
- `conceptsApi` 对象 (list, roots, tree, search, get, papers, researchPoints)

### graph.ts

包含：
- `graphApi` 对象 (stats, data, treeData)

### dedup.ts

包含：
- `dedupApi` 对象 (scan, scanStatus, execute)
- 类型：`MergeSuggestion`, `ExecuteDetail`, `FloatingConceptDetail`, `DedupExecuteResponse`, `ScanStatusResponse`

### batch.ts

包含：
- `batchApi` 对象 (upload, process, status)
- 类型：`BatchUploadResponse`, `BatchProcessResponse`, `BatchJobStatus`

### export.ts

包含：
- `exportApi` 对象 (obsidian, download, canvas, downloadCanvas, html, downloadHtml)
- 类型：`ExportResponse`

### llm.ts

包含：
- `llmApi` 对象 (providers, getConfig, saveConfig, test)
- 类型：`LLMProviderConfig`, `LLMConfigResponse`, `LLMTestResponse`, `ProviderInfo`, `FunctionGroup`

### s2.ts

包含：
- `s2Api` 对象 (getConfig, saveConfig, test, enhance)
- `recommendationApi` 对象 (getGraphRecommendations, searchPapersByConcept, searchPapersByConcepts)
- `s2PaperApi` 对象 (addMetadata, downloadAndProcess)
- 类型：`S2ConfigResponse`, `S2ConfigRequest`, `S2TestResponse`, `RecommendedPaper`, `RecommendationsResponse`, `ConceptSearchPapersResponse`, `AddFromS2Request`, `AddFromS2Response`

### citation.ts

包含：
- `citationApi` 对象 (getGraph, build, getContext)
- 类型：`CitationRef`, `CitationNode`, `CitationEdge`, `CitationGraphData`, `CitationBuildResponse`, `CitationContext`

### folders.ts

包含：
- `foldersApi` 对象 (list, create, update, delete)
- 类型：`FolderResponse`, `CreateFolderRequest`, `UpdateFolderRequest`

### agent.ts

包含：
- `agentApi` 对象 (chat, chatStream, chatStreamFetch, startDeepResearch, getResearchStatus, getResearchReport)
- 类型：`AgentType`, `AgentMessage`, `AgentContextSummary`, `ConceptGraphData`, `AttachmentType`, `AgentChatResponse`
- 导入 `ChatAttachment` 从 `stores/agentStore`

### conversations.ts

包含：
- `conversationsApi` 对象 (create, list, get, updateTitle, delete, addMessage, getDeviceId)
- 类型：`Conversation`, `Message`, `ConversationDetail`

### index.ts

```typescript
// Re-export everything for backward compatibility
export { default as api } from './client'
export { getOrCreateDeviceId } from './client'

export { papersApi } from './papers'
export type { PaperContribution, ProcessSingleResponse } from './papers'

export { conceptsApi } from './concepts'

export { graphApi } from './graph'

export { dedupApi } from './dedup'
export type { ScanStatusResponse } from './dedup'

export { batchApi } from './batch'

export { exportApi } from './export'

export { llmApi } from './llm'

export { s2Api, recommendationApi, s2PaperApi } from './s2'
export type { S2ConfigResponse, S2ConfigRequest, S2TestResponse } from './s2'

export { citationApi } from './citation'

export { foldersApi } from './folders'

export { agentApi } from './agent'

export { conversationsApi } from './conversations'
export type { Conversation, Message, ConversationDetail } from './conversations'
```

---

## 向后兼容

现有代码无需修改：
```typescript
// 仍然有效
import { papersApi, conceptsApi, api } from '@/lib/api'
```

---

## 实现步骤

1. 创建 `lib/api/` 目录结构
2. 创建 `client.ts` (axios 实例)
3. 依次创建各模块文件
4. 创建 `index.ts` 重新导出
5. 验证导入正常
6. 删除旧 `lib/api.ts`
7. 提交

---

## 预期结果

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| 最大文件行数 | 675 | ~80 |
| 文件数 | 1 | 14 |
| 类型可测试 | ❌ | ✅ |
| 向后兼容 | N/A | ✅ |