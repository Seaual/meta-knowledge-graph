---
name: competitor-analysis
description: |
  Activate when analyzing competitors for market research, competitive intelligence, or product strategy.
  Handles: competitor feature analysis, tech stack identification, SWOT analysis, pricing comparison.
  Keywords: competitor, competitive analysis, market research, SWOT, teardown, tech stack, feature matrix.
  Do NOT use for: general web search (use web-research instead), SEO analysis (use dedicated SEO tools).
  # Adapted from: inferen-sh/skills@competitor-teardown
allowed-tools: [WebSearch, WebFetch, Read]
---

# Competitor Analysis Skill

竞争对手分析技能，用于功能对比、技术栈识别、可复用模式提取。

## 前置检查

确保有网络访问权限。如需截图功能，需配置 `infsh` CLI（可选）。

## 执行步骤

### Step 1：收集竞品基本信息

使用 WebSearch 搜索竞品的基本信息：
- 公司背景、融资情况、团队规模
- 产品定位、目标用户群体
- 市场份额、用户增长趋势

```markdown
搜索关键词示例：
- "[竞品名] company overview funding"
- "[竞品名] vs alternatives comparison"
- "[竞品名] market share 2024"
```

### Step 2：分析产品功能

访问竞品官网，分析核心功能模块：
- 主要功能列表
- 用户流程设计
- 差异化特性

输出功能矩阵表格：

| 功能模块 | 我们的产品 | 竞品 A | 竞品 B |
|---------|:---:|:---:|:---:|
| 功能 1 | ✅ | ✅ | ❌ |
| 功能 2 | ⚠️ 部分 | ✅ | ✅ |

### Step 3：技术栈识别（新增）

分析竞品使用的技术栈：

**识别方法**：
1. 查看 HTML 源码中的 meta 标签、script 引用
2. 使用浏览器开发者工具检查网络请求
3. 查看公开的技术文档或招聘信息
4. 使用 Wappalyzer 等工具

**输出格式**：

| 技术层 | 识别到的技术 | 置信度 | 识别依据 |
|-------|------------|:------:|---------|
| 前端框架 | React 18 | 高 | script 标签含 react-dom |
| 构建工具 | Next.js | 高 | _next/static 路径特征 |
| UI 库 | Tailwind CSS | 高 | class 命名模式 |
| 后端 | Node.js | 中 | 招聘信息提及 |
| 数据库 | PostgreSQL | 低 | 推测 |

**置信度定义**：
- **高**：有明确技术特征（源码、HTTP 响应头、官方文档）
- **中**：有间接证据（招聘信息、相似产品对比）
- **低**：基于推测或行业惯例

### Step 4：定价策略分析

分析竞品的定价模型：
- 价格层级（免费版/入门版/专业版/企业版）
- 计费方式（按用户/按用量/一次性）
- 隐藏成本（设置费、API 调用限制）

### Step 5：SWOT 分析

为每个竞品生成 SWOT 矩阵：

```markdown
### [竞品名] — SWOT

| 优势 | 劣势 |
|-----|-----|
| • 品牌知名度高 | • 功能迭代慢 |
| • 集成生态丰富 | • 学习曲线陡峭 |

| 机会 | 威胁 |
|-----|-----|
| • 尚未推出 AI 功能 | • 新兴 AI 原生竞品 |
| • 中端市场空白 | • 用户流失率上升 |
```

### Step 6：用户评价挖掘

搜索第三方评价平台：
- G2、Capterra（B2B 软件）
- App Store、Google Play（移动应用）
- Reddit、Twitter（真实用户反馈）

提取关键信息：
- 最受好评的功能
- 最常抱怨的问题
- 用户流失原因
- 功能请求

### Step 7：生成分析报告

输出结构化报告到 `.claude/workspace/competitor-analysis.md`：

```markdown
# 竞品分析报告

## 执行摘要
[一句话总结关键发现]

## 竞品概览
| 维度 | 竞品 A | 竞品 B |
|-----|-------|-------|
| 定位 | ... | ... |
| 用户规模 | ... | ... |
| 定价 | ... | ... |

## 功能对比矩阵
[功能对比表格]

## 技术栈分析
[技术栈识别表格]

## SWOT 分析
[各竞品 SWOT]

## 可复用模式
[从竞品中学习的设计模式或技术方案]

## 建议行动
1. [基于分析的具体建议]
2. [...]
```

## 输出格式

分析报告保存到 `.claude/workspace/competitor-analysis.md`，使用 Markdown 格式。

## 完成标准

- [ ] 至少分析了 2 个竞品
- [ ] 功能对比矩阵完整
- [ ] 技术栈识别包含置信度
- [ ] SWOT 分析有具体依据
- [ ] 报告包含可操作建议

## 错误处理

| 错误 | 原因 | 处理方式 |
|-----|------|---------|
| 无法访问竞品网站 | 网络限制或网站下线 | 使用 WebSearch 搜索缓存信息 |
| 技术栈无法识别 | 无公开技术信息 | 标注"无法识别"，不强行推测 |
| 评价数据不足 | 新产品或小众产品 | 使用更广泛的关键词搜索 |

## 使用示例

用户输入：「分析 Notion 和 Obsidian 这两个笔记应用的竞争情况」
Skill 行为：
1. 搜索两个产品的公司背景和市场数据
2. 对比核心功能（块编辑、双向链接、数据库等）
3. 识别技术栈（Notion: React, Obsidian: Electron）
4. 分析定价策略
5. 挖掘用户评价
6. 输出完整的竞品分析报告

## 与原 skill 的差异

此 skill 改编自 `inferen-sh/skills@competitor-teardown`，主要变更：
1. **新增** Step 3：技术栈识别（含置信度评估）
2. **简化** 命令示例（移除对 infsh CLI 的依赖，使用通用 WebSearch）
3. **调整** 输出格式对齐 Team 的 workspace 协议