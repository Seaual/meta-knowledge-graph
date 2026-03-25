# LLM Configuration Feature Design Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add LLM configuration UI to the homepage, allowing users to configure multiple LLM providers through a user-friendly interface.

**Architecture:** Frontend modal for configuration, backend API for CRUD operations and testing, SQLite persistence for configurations.

---

## Deliverables

### 1. UI Changes

**Home Page - Quick Actions Section:**
- Add a third card "LLM 配置" with settings icon
- Display current active provider status (e.g., "当前: OpenAI (gpt-4)")

**Configuration Modal:**
- Mode switcher: Single Provider / Per-Function Allocation
- Provider selector dropdown
- API Key input (password type)
- Base URL input (optional)
- Model input
- Test Connection button
- Save Configuration button

### 2. Backend API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/llm/config` | GET | Get current LLM configuration |
| `/api/llm/config` | POST | Save LLM configuration |
| `/api/llm/test` | POST | Test LLM connection |
| `/api/llm/providers` | GET | List available providers |

### 3. Database Schema

```sql
CREATE TABLE llm_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL DEFAULT 'single',  -- 'single' or 'per_function'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE llm_provider_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_id INTEGER NOT NULL,
    function_group TEXT,  -- NULL for single mode, or 'paper_parsing', 'concept_extraction', 'research_analysis'
    provider TEXT NOT NULL,  -- 'openai', 'anthropic', 'google', 'dashscope', 'openrouter', 'minimax', 'claude_cli'
    api_key TEXT NOT NULL,
    base_url TEXT,
    model TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (config_id) REFERENCES llm_config(id)
);
```

### 4. Supported Providers

| Provider | Value | Requires API Key | Notes |
|----------|-------|------------------|-------|
| Claude Code CLI | `claude_cli` | No | Uses Claude Code's configured API (for testing) |
| OpenAI Compatible | `openai` | Yes | Default base: https://api.openai.com/v1 |
| Anthropic Claude | `anthropic` | Yes | Uses official Anthropic SDK |
| Google Gemini | `google` | Yes | Uses google-generativeai |
| Alibaba DashScope | `dashscope` | Yes | Uses qwen models |
| OpenRouter | `openrouter` | Yes | Base: https://openrouter.ai/api/v1 |
| MiniMax | `minimax` | Yes | Requires custom base URL |

> **Claude Code CLI**: 便捷测试选项，自动使用 Claude Code 已配置的 API，无需额外配置。适合本地开发测试场景。

### 5. Function Groups (Per-Function Mode)

| Group | Value | Description |
|-------|-------|-------------|
| 论文解析 | `paper_parsing` | PDF parsing and metadata extraction |
| 概念提取 | `concept_extraction` | LLM concept tree extraction |
| 研究分析 | `research_analysis` | Research point discovery, deduplication |

---

## Implementation Tasks

### Task 1: Database Schema
- [ ] Add `llm_config` and `llm_provider_config` tables to database.py
- [ ] Add CRUD methods for LLM configuration

### Task 2: Backend API
- [ ] Create `backend/routes/llm.py` with config endpoints
- [ ] Add provider list endpoint
- [ ] Add connection test endpoint
- [ ] Update `get_extractor()` to use database config

### Task 3: Frontend UI
- [ ] Add LLM config card to Home.tsx
- [ ] Create LLMConfigModal component
- [ ] Add llmApi to api.ts
- [ ] Wire up test connection and save functionality

### Task 4: Integration
- [ ] Update papers.py to use database config
- [ ] Update concepts.py to use database config
- [ ] Test with multiple providers

---

## Configuration Flow

```
User clicks "LLM 配置" card
     ↓
Modal opens with current config (if any)
     ↓
User selects mode (Single / Per-Function)
     ↓
User selects provider and enters credentials
     ↓
User clicks "Test Connection"
     ↓
Backend sends test request to LLM
     ↓
Success → User clicks "Save Configuration"
     ↓
Config persisted to database
     ↓
Subsequent LLM calls use saved config
```

---

## Security Considerations

1. API Keys stored in database should be considered sensitive
2. Frontend should mask API keys in display
3. Consider encryption for stored API keys (future enhancement)
4. Test connection should have timeout and error handling

---

## Error Handling

| Scenario | Response |
|----------|----------|
| Invalid API Key | "API Key 无效，请检查后重试" |
| Network Error | "网络连接失败，请检查 Base URL" |
| Model Not Found | "模型不存在，请确认模型名称" |
| Rate Limited | "请求过于频繁，请稍后重试" |
| No Config | Prompt user to configure before using LLM features |