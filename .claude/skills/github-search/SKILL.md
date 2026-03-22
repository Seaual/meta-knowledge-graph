---
name: github-search
description: |
  Activate when searching GitHub for code, repositories, issues, or PRs.
  Handles: code search, repo search, issue/PR search.
  Keywords: github, search code, find repo, github issues, search repositories.
  Do NOT use for: cloning repositories (use Bash git clone), general web search (use web-research).
allowed-tools: [Bash, Read]
---

# GitHub Search Skill

通过 MCP 或 GitHub CLI 搜索 GitHub 代码、仓库、Issue 和 PR。

## 前置检查

检查可用的搜索方式（按优先级）：

1. **MCP GitHub Server**（推荐）— 需配置 `@anthropic-ai/mcp-server-github`
2. **GitHub CLI** — 需安装 `gh` 命令行工具
3. **WebSearch** — 降级方案，通过网页搜索

```bash
# 检查 gh CLI
gh --version

# 检查 MCP（通过 settings.json 配置）
```

## 执行步骤

### Step 1：确定搜索类型

根据用户需求选择搜索类型：
- `code` — 搜索代码片段
- `repos` — 搜索仓库
- `issues` — 搜索 Issue
- `prs` — 搜索 Pull Request

### Step 2：构建搜索查询

GitHub 搜索语法支持：
- `language:python` — 按语言过滤
- `owner:anthropics` — 按组织过滤
- `repo:owner/name` — 指定仓库
- `label:bug` — 按标签过滤（Issue/PR）
- `state:open` — 按状态过滤

### Step 3：执行搜索

**方式 A：使用 GitHub CLI**

```bash
# 搜索代码
gh search code "authentication" --language python --limit 20

# 搜索仓库
gh search repos "claude code agent" --limit 10

# 搜索 Issue
gh search issues "bug label:critical" --owner anthropics --limit 15

# 搜索 PR
gh search prs "feature:auth" --state merged --limit 10
```

**方式 B：使用 MCP（如已配置）**

通过 MCP 工具调用 GitHub API。

**方式 C：WebSearch 降级**

```bash
# 通过网页搜索
# 搜索代码: "site:github.com \"authentication\" language:python"
# 搜索仓库: "site:github.com topic:claude-agent"
```

### Step 4：解析和展示结果

将搜索结果整理为可读格式：

**代码搜索结果**：
```markdown
| 文件 | 仓库 | 匹配行 |
|-----|-----|-------|
| auth.py | owner/repo | `def authenticate(user, pwd):` |
```

**仓库搜索结果**：
```markdown
| 仓库名 | 描述 | Stars | 语言 |
|-------|-----|------|-----|
| owner/repo | Description here | 1.2k | Python |
```

**Issue/PR 搜索结果**：
```markdown
| 标题 | 状态 | 作者 | 创建时间 |
|-----|-----|-----|---------|
| Bug in auth | open | user1 | 2024-01-15 |
```

## 输出格式

搜索结果保存到 `.claude/workspace/github-search-results.md`（如需要）。

## 完成标准

- [ ] 搜索查询正确执行
- [ ] 结果以表格形式清晰展示
- [ ] 包含足够的上下文信息

## 错误处理

| 错误 | 原因 | 处理方式 |
|-----|------|---------|
| `gh: command not found` | 未安装 GitHub CLI | 提示安装或使用 WebSearch |
| `rate limit exceeded` | API 限额用尽 | 等待重置或配置 GITHUB_TOKEN |
| 无结果 | 查询条件过严 | 放宽搜索条件，扩大范围 |

## 配置要求

### MCP 配置（推荐）

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

### 环境变量

- `GITHUB_TOKEN`（可选）— 提高 API 限额

### GitHub CLI 安装

```bash
# macOS
brew install gh

# Linux
sudo apt install gh

# Windows
winget install GitHub.cli
```

## 使用示例

用户输入：「在 GitHub 上搜索处理 OAuth 认证的 Python 代码」
Skill 行为：
1. 使用 `gh search code` 搜索
2. 添加 `--language python` 过滤
3. 展示匹配的代码文件和仓库
输出样例：
```markdown
找到 25 个代码文件：

| 文件 | 仓库 | 匹配 |
|-----|-----|-----|
| oauth.py | example/auth-lib | `class OAuthHandler:` |
| auth_utils.py | another/sdk | `def oauth_flow():` |
```