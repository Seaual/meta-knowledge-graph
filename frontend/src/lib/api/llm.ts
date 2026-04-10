// frontend/src/lib/api/llm.ts
import api from "./client";

export interface LLMProviderConfig {
  function_group?: string;
  provider: string;
  api_key?: string;
  base_url?: string;
  model?: string;
  is_active: boolean;
}

export interface LLMConfigResponse {
  mode: string;
  providers: LLMProviderConfig[];
}

export interface LLMTestResponse {
  success: boolean;
  message: string;
  model?: string;
}

export interface ProviderInfo {
  value: string;
  label: string;
  requires_api_key: boolean;
  default_base_url?: string;
}

export interface FunctionGroup {
  value: string;
  label: string;
}

export const llmApi = {
  providers: () =>
    api.get<{ providers: ProviderInfo[]; function_groups: FunctionGroup[] }>(
      "/llm/providers"
    ),
  getConfig: () => api.get<LLMConfigResponse>("/llm/config"),
  saveConfig: (config: LLMConfigResponse) =>
    api.post<LLMConfigResponse>("/llm/config", config),
  test: (params: {
    provider: string;
    api_key?: string;
    base_url?: string;
    model?: string;
  }) => api.post<LLMTestResponse>("/llm/test", params),
};
