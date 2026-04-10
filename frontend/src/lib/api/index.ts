// frontend/src/lib/api/index.ts
// Re-export everything for backward compatibility

export { default as api } from "./client";
export { getOrCreateDeviceId } from "./client";

export { papersApi } from "./papers";
export type { PaperContribution, ProcessSingleResponse } from "./papers";

export { conceptsApi } from "./concepts";

export { graphApi } from "./graph";

export { dedupApi } from "./dedup";
export type { ScanStatusResponse } from "./dedup";

export { batchApi } from "./batch";

export { exportApi } from "./export";

export { llmApi } from "./llm";

export { s2Api, recommendationApi, s2PaperApi } from "./s2";
export type { S2ConfigResponse, S2ConfigRequest, S2TestResponse } from "./s2";

export { citationApi } from "./citation";

export { foldersApi } from "./folders";

export { agentApi } from "./agent";

export { conversationsApi } from "./conversations";
export type {
  Conversation,
  Message,
  ConversationDetail,
} from "./conversations";
