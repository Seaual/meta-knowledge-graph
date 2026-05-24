# Agent Harness / 自动学习机设计草案

> Project: `meta-knowledge-graph`
> Date: `2026-04-26`
> Status: Draft v0.1

## 1. 背景

`Meta Knowledge Graph` 当前已经具备较强的学术知识处理能力：

- 论文上传与解析
- Semantic Scholar 元数据增强
- 概念抽取与知识图谱构建
- Chat-based agent 问答
- 深度研究与研究点发现

但当前系统的主轴仍是：

`论文 -> 结构化知识 -> 图谱/问答`

如果目标升级为“自动学习机”，系统主轴需要演进为：

`研究目标 -> 文献摄取 -> 知识建模 -> 假设生成 -> 实验执行 -> 写作沉淀 -> 记忆更新`

因此，下一个阶段不应理解为“再加几个 agent”，而应理解为：

`将现有 MKG 演进为面向研究任务的 Agent Harness / Research Workspace`

## 2. 产品定义

### 2.1 一句话定义

一个围绕研究项目长期运行的多智能体研究系统，具备论文阅读、知识组织、假设生成、实验编排、论文写作和长期记忆能力。

### 2.2 与当前 MKG 的差异

当前 MKG 更像：

- 学术知识图谱引擎
- 论文分析与研究点发现工具
- 带 agent 的研究问答系统

目标中的 Agent Harness 更像：

- 研究项目工作台
- 研究流程编排系统
- 具备自治能力的研究操作系统

### 2.3 边界

第一阶段不追求：

- 完整桌面操作系统
- 完全自治的端到端论文生成
- 大规模远程算力编排

第一阶段聚焦：

- 项目制研究工作区
- 论文阅读与证据管理
- 研究任务与假设管理
- 写作辅助闭环

## 3. 设计原则

### 3.1 项目优先，而非聊天优先

研究状态不能散落在对话历史中。系统的一等公民应是 `Project`，不是 `Conversation`。

### 3.2 证据优先，而非生成优先

任何结论、草稿、研究建议，都应该尽量绑定到可回溯的证据：

- 论文段落
- 图表
- 元数据
- 实验结果

### 3.3 半自动先于全自动

先做 `Copilot`，再做 `Operator`，最后做 `Autonomous Researcher`。

### 3.4 失败经验也是资产

实验失败、被否定的假设、低质量草稿、错误检索路径都应该被记录，而不是覆盖。

### 3.5 同一项目内闭环

论文、笔记、任务、实验、草稿、记忆，应统一挂在同一个项目容器下。

## 4. 目标形态

### 4.1 三阶段演进

#### Phase 1: Research Copilot

用户主导研究目标，系统协助：

- 读论文
- 记笔记
- 做综述
- 生成提纲和草稿
- 形成候选假设

#### Phase 2: Research Operator

系统开始自动推进任务：

- 自动抓取新论文
- 自动更新综述
- 自动生成实验计划
- 自动跑可控任务
- 自动整理结果

#### Phase 3: Auto Learning Machine

系统围绕长期研究目标持续自我推进：

- 自主维护研究 agenda
- 自主管理假设池
- 自主安排实验顺序
- 自主更新写作草稿
- 根据反馈修正策略

## 5. 用户场景

### 5.1 场景 A：论文阅读

用户打开一篇论文，看到：

- PDF 阅读区
- 章节导航
- 摘录/批注面板
- 右侧对话助手
- 证据引用面板

用户可以：

- 针对当前段落提问
- 抽取方法、实验设置、结论
- 保存结构化笔记
- 将某段内容链接到项目中的 hypothesis 或 draft

### 5.2 场景 B：文献综述

用户在某个项目下聚合 20-50 篇论文，系统帮助：

- 聚类研究方向
- 对比方法与数据集
- 提取争议点
- 识别研究空白
- 生成综述提纲

### 5.3 场景 C：实验设计与跟踪

用户选中某个候选假设，系统生成：

- baseline 建议
- 实验变量
- 参数表
- 预期指标
- 风险提示

后续可把实验运行和日志挂回该假设。

### 5.4 场景 D：论文写作

系统支持：

- 生成章节提纲
- 基于证据写段落初稿
- 自动补充候选引用
- 对段落做“证据不足”提醒

## 6. 信息架构

建议新增以下一级页面或工作区：

### 6.1 Projects

项目列表页，展示：

- 项目名称
- 研究主题
- 当前阶段
- 最近活动
- 挂载论文数量
- 假设/实验/草稿数量

### 6.2 Project Workspace

研究项目总工作台，聚合：

- 项目摘要
- 最近任务
- 研究 timeline
- 当前重点论文
- 当前草稿
- 当前实验

### 6.3 Paper Reader

单篇论文工作区：

- PDF/文本阅读区
- 摘录批注
- 结构化解析
- 对话助手
- 证据定位

### 6.4 Literature Review Board

多论文对比工作区：

- 方法对比表
- 时间线
- 概念图谱
- 争议点
- 空白点

### 6.5 Hypothesis Lab

研究假设管理页：

- 假设描述
- novelty / feasibility / impact
- 支持证据
- 反例
- 状态流转

### 6.6 Experiment Runner

实验工作区：

- 计划
- 参数
- 执行状态
- 日志
- 结果摘要
- Artifact 列表

### 6.7 Writing Studio

写作工作区：

- 提纲
- 章节
- 段落草稿
- 引用建议
- 审稿式检查

### 6.8 Agent Timeline

展示 agent 的动作轨迹：

- 做了什么
- 为什么这么做
- 结果如何
- 是否需要用户介入

## 7. 前端演进建议

现有页面可按以下方式重构：

- `Home` 保留为总览入口
- `Papers` 演进为 `Paper Desk / Reader`
- `Chat` 不再作为全局主页面，而是变成工作区右侧面板
- `Concepts` 保留为项目内知识图谱视图
- `Settings` 保留

建议新增：

- `Projects.tsx`
- `ProjectWorkspace.tsx`
- `Experiments.tsx`
- `Drafts.tsx`

建议新增核心组件：

- `PaperReader`
- `WorkspaceRightChat`
- `EvidencePanel`
- `HypothesisPanel`
- `ExperimentRunPanel`
- `DraftOutlinePanel`
- `AgentTimelinePanel`

## 8. 后端架构演进

### 8.1 当前结构

当前后端已经具备以下良好基础：

- `backend/routes/*` API 分层
- `backend/services/*` 业务服务层
- `mkg/agent/*` LangGraph agent 层
- SQLite 持久化

### 8.2 目标结构

建议在现有结构上扩展，而不是重写：

```text
backend/
  routes/
    projects.py
    experiments.py
    drafts.py
    review.py
    notes.py
  services/
    project_service.py
    note_service.py
    experiment_service.py
    draft_service.py
    evidence_service.py
    memory_service.py

mkg/
  agent/
    graph.py
    memory.py
    tools.py
    nodes/
      planner.py
      reader.py
      reviewer.py
      hypothesis.py
      writer.py
      experimenter.py
      critic.py
```

### 8.3 核心分层

建议明确四层：

#### Knowledge Layer

负责：

- 论文元数据
- 论文全文/解析结果
- 概念图谱
- 引用关系

#### Research State Layer

负责：

- 项目
- 任务
- 假设
- 草稿
- 实验
- 证据
- 记忆

#### Agent Orchestration Layer

负责：

- 任务拆解
- agent 路由
- 状态流转
- 结果合并

#### Execution Layer

负责：

- 本地脚本执行
- 日志采集
- artifact 保存
- 后续可扩展到容器/远程运行

## 9. 数据模型建议

### 9.1 新增核心表

#### `projects`

字段建议：

- `id`
- `name`
- `description`
- `domain`
- `goal`
- `status`
- `mode` (`copilot` / `operator` / `autonomous`)
- `created_at`
- `updated_at`

#### `project_papers`

字段建议：

- `project_id`
- `paper_doi`
- `role` (`seed` / `reference` / `baseline` / `related`)
- `priority`
- `added_at`

#### `paper_notes`

字段建议：

- `id`
- `project_id`
- `paper_doi`
- `page`
- `section`
- `selected_text`
- `note_type` (`summary` / `quote` / `critique` / `question`)
- `content`
- `created_by`
- `created_at`

#### `claims`

字段建议：

- `id`
- `project_id`
- `text`
- `claim_type` (`finding` / `assumption` / `hypothesis` / `critique`)
- `confidence`
- `status`
- `created_by`
- `created_at`

#### `evidence_links`

字段建议：

- `id`
- `project_id`
- `target_type` (`claim` / `draft_section` / `hypothesis`)
- `target_id`
- `source_type` (`paper_snippet` / `citation` / `experiment_result`)
- `source_ref`
- `strength`
- `created_at`

#### `research_tasks`

字段建议：

- `id`
- `project_id`
- `task_type`
- `title`
- `description`
- `status`
- `priority`
- `assigned_agent`
- `input_payload`
- `output_payload`
- `created_at`
- `updated_at`

#### `hypotheses`

字段建议：

- `id`
- `project_id`
- `title`
- `description`
- `novelty_score`
- `feasibility_score`
- `impact_score`
- `status`
- `support_count`
- `created_at`

#### `experiment_runs`

字段建议：

- `id`
- `project_id`
- `hypothesis_id`
- `name`
- `status`
- `plan`
- `config_json`
- `script_path`
- `log_path`
- `result_summary`
- `started_at`
- `finished_at`

#### `experiment_artifacts`

字段建议：

- `id`
- `run_id`
- `artifact_type`
- `path`
- `metadata_json`
- `created_at`

#### `drafts`

字段建议：

- `id`
- `project_id`
- `title`
- `draft_type` (`survey` / `paper` / `proposal` / `report`)
- `status`
- `current_version`
- `created_at`
- `updated_at`

#### `draft_sections`

字段建议：

- `id`
- `draft_id`
- `section_key`
- `title`
- `content`
- `order_index`
- `status`
- `updated_at`

#### `agent_memories`

字段建议：

- `id`
- `project_id`
- `memory_type` (`semantic` / `episodic` / `working`)
- `title`
- `content`
- `importance`
- `source_task_id`
- `created_at`

#### `agent_actions`

字段建议：

- `id`
- `project_id`
- `task_id`
- `agent_name`
- `action_type`
- `input_summary`
- `output_summary`
- `status`
- `created_at`

### 9.2 与现有表的关系

应尽量复用已有：

- `papers`
- `concepts`
- `concept_relations`
- `conversations`
- `messages`

演进策略：

- `papers` 仍是论文主表
- `conversations` 变成项目内辅助对话，而非唯一状态中心
- 新增 `projects` 后，`conversation` 应可选地绑定 `project_id`

## 10. Agent 设计

### 10.1 第一阶段角色

#### `planner`

负责：

- 理解用户目标
- 拆解研究任务
- 选择下游 agent
- 组织输出

#### `reader`

负责：

- 读取论文内容
- 提炼结构化笔记
- 识别方法/实验/结论
- 生成 evidence candidates

#### `reviewer`

负责：

- 横向对比多篇论文
- 找冲突、趋势、研究空白
- 输出综述视角摘要

#### `hypothesis_agent`

负责：

- 基于综述与图谱提出假设
- 给出 novelty / feasibility / impact
- 组织支持与反对证据

#### `writer`

负责：

- 生成提纲
- 按章节写初稿
- 给段落补候选引用
- 输出“证据不足”警告

#### `experimenter`

负责：

- 生成实验计划
- 制作实验配置
- 后续对接脚本执行
- 汇总结果并反馈给项目状态

### 10.2 第二阶段角色

建议后续再加入：

- `critic`
- `memory_curator`
- `scheduler`
- `replicator`

### 10.3 状态管理

现有 agent 状态主要围绕单次对话，后续应升级为项目状态：

- `project_id`
- `current_goal`
- `active_papers`
- `active_claims`
- `active_hypotheses`
- `current_draft_id`
- `current_experiment_run_id`
- `working_memory`

## 11. API 设计建议

### 11.1 项目接口

- `POST /api/projects`
- `GET /api/projects`
- `GET /api/projects/{project_id}`
- `PATCH /api/projects/{project_id}`
- `GET /api/projects/{project_id}/timeline`

### 11.2 论文与笔记接口

- `GET /api/projects/{project_id}/papers`
- `POST /api/projects/{project_id}/papers/link`
- `POST /api/papers/{doi}/notes`
- `GET /api/papers/{doi}/notes`
- `POST /api/papers/{doi}/ask`
- `POST /api/evidence/locate`

### 11.3 综述与假设接口

- `POST /api/projects/{project_id}/review/generate`
- `GET /api/projects/{project_id}/claims`
- `POST /api/projects/{project_id}/hypotheses`
- `POST /api/projects/{project_id}/hypotheses/generate`
- `PATCH /api/hypotheses/{hypothesis_id}`

### 11.4 实验接口

- `POST /api/projects/{project_id}/experiments/plan`
- `POST /api/projects/{project_id}/experiments/run`
- `GET /api/experiments/{run_id}`
- `GET /api/experiments/{run_id}/logs`
- `POST /api/experiments/{run_id}/artifacts`

### 11.5 写作接口

- `POST /api/projects/{project_id}/drafts`
- `GET /api/drafts/{draft_id}`
- `POST /api/drafts/{draft_id}/outline/generate`
- `POST /api/drafts/{draft_id}/sections/{section_id}/write`
- `POST /api/drafts/{draft_id}/review`

## 12. 工作流设计

### 12.1 阅读工作流

`Project -> Select Paper -> Read -> Annotate -> Ask -> Save Notes -> Link Evidence`

### 12.2 综述工作流

`Project -> Select Corpus -> Compare -> Extract Claims -> Discover Gaps -> Generate Review Outline`

### 12.3 假设工作流

`Review Findings -> Generate Hypotheses -> Score -> Attach Evidence -> User Confirm`

### 12.4 写作工作流

`Project Context -> Draft Outline -> Section Drafting -> Citation Linking -> Review`

### 12.5 实验工作流

`Hypothesis -> Plan Experiment -> Generate Config -> Execute -> Collect Results -> Update Memory`

## 13. MVP 范围

### 13.1 必做

- `Project` 模型与页面
- 项目内论文挂载
- Paper Reader 基础界面
- 笔记与 evidence link
- 项目内 agent chat
- Hypothesis 基础模型
- Draft 基础模型
- 提纲和章节初稿生成

### 13.2 可延期

- 真正的实验脚本执行器
- 远程算力调度
- 多用户协作
- 完整自治调度器
- Git worktree / quest 仓库化

### 13.3 不在第一阶段

- 完整 Electron 桌面壳
- 自动投稿级论文成品
- 全自动无人值守长周期研究

## 14. 迁移策略

### 14.1 不推翻现有页面

采用渐进式演进：

- 保留 `Papers`
- 保留 `Concepts`
- 保留 `Settings`
- 将 `Chat` 降级为工作区面板
- 新增 `Projects` 作为研究主入口

### 14.2 不推翻现有 agent

继续复用：

- `mkg/agent/graph.py`
- `mkg/agent/tools.py`
- 现有 paper QA / deep research 能力

通过以下方式扩展：

- 增加项目上下文
- 增加新 nodes
- 增加 research state persistence

### 14.3 数据迁移

优先做前向兼容：

- 旧对话记录保留
- 无项目归属的旧 conversation 视为 `legacy`
- 后续逐步支持把旧 paper 挂入新 project

## 15. 参考思路来源

本设计主要吸收了以下开源方向中的共性模式：

- `ResearchClaw`: persistent research state
- `DeepScientist`: local-first research OS, copilot/autonomous dual mode
- `karpathy/autoresearch`: experiment feedback loop
- `AgentLaboratory`: literature -> experimentation -> writing pipeline
- `GPT Researcher`: research report workflow and planning
- `PaSa`: literature search specialization

本草案只吸收其产品和系统思想，不直接复制其架构实现。

## 16. 下一步实施建议

建议按以下顺序落地：

1. 新增 `projects` 数据模型与 API
2. 新增 `Projects` 页面与 `Project Workspace` 骨架
3. 将 `Chat` 嵌入项目工作区右侧
4. 增加 `paper_notes` 与 `evidence_links`
5. 增加 `hypotheses` 与 `drafts`
6. 最后再进入实验执行层

## 17. 结论

`Meta Knowledge Graph` 已经具备成为研究型 Agent Harness 的良好基础。

正确的演进路径不是“继续堆聊天能力”，而是：

- 从全局工具转为项目制工作台
- 从问答系统转为研究状态系统
- 从论文分析转为研究闭环
- 从临时上下文转为长期记忆

第一阶段应把系统做成一个强协同的 `Research Copilot Workspace`；
在此基础上，再逐步演进为真正的“自动学习机”。
