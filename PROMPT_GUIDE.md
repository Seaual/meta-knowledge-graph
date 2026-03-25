# Meta Knowledge Graph — Prompt 工程完整指南

> 本文档包含三个核心 LLM 提示词的完整诊断、设计原则和重写方案。  
> 可直接作为项目文档 `PROMPT_GUIDE.md` 使用。

---

## 目录

- [第零章：分类原则](#第零章分类原则)
- [第一章：概念提取（两阶段架构）](#第一章概念提取两阶段架构)
  - [1.1 原版问题诊断](#11-原版问题诊断)
  - [1.2 架构改动：一阶段 → 两阶段](#12-架构改动一阶段--两阶段)
  - [1.3 Stage 1 提示词：论文总结](#13-stage-1-提示词论文总结)
  - [1.4 Stage 2 提示词：核心概念提取](#14-stage-2-提示词核心概念提取)
  - [1.5 效果对比](#15-效果对比)
  - [1.6 代码集成建议](#16-代码集成建议)
- [第二章：概念合并](#第二章概念合并)
  - [2.1 原版问题诊断](#21-原版问题诊断)
  - [2.2 重写方案](#22-重写方案)
- [第三章：研究点发现](#第三章研究点发现)
  - [3.1 原版问题诊断](#31-原版问题诊断)
  - [3.2 重写方案](#32-重写方案)
- [附录：快速替换对照表](#附录快速替换对照表)

---

## 第零章：分类原则

所有提示词共享同一套分类原理。在修改任何 prompt 之前，先理解这个基础。

### 核心公理：最小可发表单元（Minimum Viable Publication Unit）

> **每个概念的层级，由学术共同体为它赋予的「最小独立学术载体」决定。**

这不是主观分类，而是学术界自身组织知识的方式的镜像：

| 学术载体 | 对应层级 | 代码 |
|----------|----------|------|
| 大学为它建系/设一级学科 | 大领域 | `field` |
| 有专门的学术会议或期刊专题 | 研究方向 | `direction` |
| 在综述论文中作为独立章节 | 子方向 | `subdirection` |
| 可表述为「给定 X，求解/优化 Y」 | 研究任务 | `task` |
| 有名字、可复现的算法流程 | 方法 | `method` |
| 方法内部的组件/技巧/设计选择 | 技术细节 | `technique` |

### 五步判定流程

从上往下问，**第一个回答"是"的就是答案**：

1. 能不能围绕它建一个大学院系？→ **field**
2. 有没有专门的学术会议或期刊专题？→ **direction**
3. 会不会在该方向的综述论文中作为独立章节？→ **subdirection**
4. 能不能表述成「给定 X，求解/优化 Y」的问题定义？→ **task**
5. 有没有具体名字和可复现的算法流程？→ **method**
6. 以上都不是 → **technique**

### 三条结构铁律

1. **严格单调性**：父节点层级必须严格高于所有子节点（field > direction > subdirection > task > method > technique）
2. **语境敏感性**：同一术语在不同论文中可以属于不同层级。"注意力机制"在 Transformer 综述中 = direction，在某个具体模型的论文中 = technique。由当前论文的语境决定。
3. **保守默认**：当概念在两个相邻层级之间模糊时，选更低（更具体）的那个。后续提升比降级的代价小。

### 判定示例

**"注意力机制"的判定：**

| 问题 | 回答 |
|------|------|
| 能建大学院系？ | 否 |
| 有专门学术会议？ | 否 |
| 综述论文中是独立章节？ | 是（在 Transformer 综述中） |
| → 结论 | **subdirection**（在综述语境中） |

但如果论文是 "BERT for Sentiment Analysis"，注意力只是使用的工具 → **technique**。

**"QMIX"的判定：**

| 问题 | 回答 |
|------|------|
| 能建大学院系？ | 否 |
| 有专门学术会议？ | 否 |
| 综述中是独立章节？ | 否（在"值分解方法"章节下被列举） |
| 能表述为问题定义？ | 否（它是解决方案，不是问题） |
| 有名字和可复现流程？ | 是 |
| → 结论 | **method** |

---

## 第一章：概念提取（两阶段架构）

### 1.1 原版问题诊断

**原文件位置**: `openclaw/pdf_parser.py` 第 428-631 行

| # | 问题 | 严重度 | 说明 |
|---|------|--------|------|
| 1 | 一次性提取所有概念 | 🔴 致命 | 不区分"论文的贡献"和"论文提到的背景"，导致图谱被背景概念淹没 |
| 2 | 层级从 6 层缩减为 5 层 | 🔴 高 | README 定义 6 层（含 subdirection/task），prompt 中丢失了 |
| 3 | 论文全文与指令混杂 | 🔴 高 | 50000 字符论文和分类规则在同一层级，LLM 容易遗忘指令 |
| 4 | 缺少思维链引导 | 🟡 中 | 直接要求输出 JSON，跳过了"先理解再提取"的关键步骤 |
| 5 | 自检清单在最末尾 | 🟡 中 | LLM 自回归生成，输出完才看到自检 = 无效 |
| 6 | confidence 无锚定标准 | 🟡 中 | 0.9 和 0.7 代表什么？没定义 |
| 7 | "判断口诀"过于主观 | 🟡 中 | "能独立成为一门课"因人而异 |

### 1.2 架构改动：一阶段 → 两阶段

**核心思想：先读懂论文，再提取概念。**

一篇论文中的概念分两类：

| 类型 | 定义 | 在图谱中的角色 | 判断标准 |
|------|------|----------------|----------|
| **背景概念** | 论文提到但非其贡献的 | 锚点：最短路径定位，不展开 | 如果这篇论文不存在，它还被广泛认知吗？→ 是 → 背景 |
| **核心概念** | 论文真正贡献/改进的 | 厚节点：展开完整子树 | 如果这篇论文不存在，它还被广泛认知吗？→ 否 → 核心 |

**比喻：锚点路径是"地址"（北京市→海淀区→中关村），贡献子树是"房间里的东西"。你不需要详细描述北京市——你只需要说清楚中关村这个房间里有什么。**

### 1.3 Stage 1 提示词：论文总结

**目标**：让 LLM 先"读懂"论文，输出结构化摘要，区分背景和贡献。

```
<s>
你是一位学术论文审稿人。请对以下论文进行结构化总结。
你的目标不是复述论文内容，而是回答一个核心问题：
**这篇论文对学术界的独特贡献是什么？它做了什么别人没做过的事？**
</s>

<paper>
<title>{title}</title>
<authors>{authors}</authors>
<abstract>{abstract}</abstract>
<body>{full_text[:50000]}</body>
</paper>

<task>
请输出以下 JSON 结构：

{
  "one_sentence_summary": "用一句话概括这篇论文（不超过50字）",

  "research_context": {
    "field": "所属大领域",
    "direction": "所属研究方向",
    "existing_gap": "论文试图填补的研究空白（1-2句话）"
  },

  "core_contributions": [
    {
      "type": "new_method | new_framework | new_dataset | new_finding | improvement | theoretical",
      "claim": "贡献的具体描述（1句话）",
      "novelty": "与已有工作相比，新在哪里（1句话）"
    }
  ],

  "methodology_summary": {
    "approach": "核心方法的一句话概述",
    "key_components": ["方法中最关键的2-3个技术组件"],
    "baselines": ["对比的基线方法"]
  },

  "results_summary": {
    "datasets": ["使用的数据集"],
    "metrics": ["评估指标"],
    "main_finding": "最重要的实验结论（1句话）"
  },

  "background_concepts": ["论文提及但非其贡献的已有概念"],
  "novel_concepts": ["论文首次提出或深入探讨的概念"]
}
</task>

<rules>
关键判断规则：
- "background_concepts" vs "novel_concepts" 的区分是最重要的。
  判断标准：如果这篇论文不存在，这个概念还会被学术界广泛认知吗？
  会 → background。不会 → novel。
- core_contributions 通常只有 1-3 个。超过 5 个说明没有区分"贡献"和"论文提到的东西"。
- 所有内容使用中文。国际通用专有名词（Transformer、BERT）可保留英文。
</rules>

只输出 JSON，不要其他内容。
```

#### Stage 1 输出示例

```json
{
  "one_sentence_summary": "提出 Attention-QMIX 算法，通过注意力机制解决多智能体值分解中的信用分配问题",
  "research_context": {
    "field": "人工智能",
    "direction": "多智能体强化学习",
    "existing_gap": "现有值分解方法使用固定权重混合各智能体Q值，无法根据场景动态调整信用分配"
  },
  "core_contributions": [
    {
      "type": "new_method",
      "claim": "提出注意力加权的值分解网络，根据智能体观测动态计算混合权重",
      "novelty": "首次将注意力机制引入值分解框架，替代 QMIX 的超网络固定权重方式"
    },
    {
      "type": "improvement",
      "claim": "在 SMAC 困难场景上超越 QMIX 和 QPLEX",
      "novelty": "在需要复杂协作的场景中提升 12-18%，简单场景持平"
    }
  ],
  "methodology_summary": {
    "approach": "在 QMIX 混合网络中用多头注意力替代超网络，实现动态信用分配",
    "key_components": ["多头注意力混合模块", "智能体观测编码器", "单调性约束保持"],
    "baselines": ["QMIX", "QPLEX", "WQMIX", "MAPPO"]
  },
  "results_summary": {
    "datasets": ["SMAC", "Google Research Football"],
    "metrics": ["测试胜率", "平均累计回报"],
    "main_finding": "在困难场景中胜率提升 12-18%，简单场景持平"
  },
  "background_concepts": ["人工智能", "强化学习", "多智能体系统", "Q学习", "值函数分解", "QMIX", "QPLEX"],
  "novel_concepts": ["Attention-QMIX", "注意力加权混合", "动态信用分配权重"]
}
```

### 1.4 Stage 2 提示词：核心概念提取

**目标**：基于 Stage 1 的摘要，只提取核心贡献对应的概念树，背景概念仅作锚点。

```
<s>
你是一位学术知识图谱构建专家。你的任务是基于论文总结，构建一棵精炼的概念树。

关键原则——区分"锚点"和"贡献"：
- **锚点路径**：从根节点到论文核心贡献的最短路径。只需存在，不展开子树。作用是定位"这篇论文属于哪里"。
- **贡献子树**：论文真正贡献的概念。展开详细子节点。这些是图谱中因为这篇论文而新增的知识。
</s>

<paper_summary>
{Stage 1 的完整 JSON 输出}
</paper_summary>

{如果图谱非空，插入以下部分：}
<existing_graph>
当前知识图谱中已有的概念。请优先复用已有节点作为锚点，避免重复创建。
{已有概念树 JSON}
</existing_graph>

<taxonomy>
层级定义（基于"最小可发表单元"原则）：
- field：能建大学院系 → 如"人工智能"
- direction：有专门学术会议 → 如"多智能体强化学习"
- subdirection：综述论文的独立章节 → 如"值分解方法"
- task：可表述为"给定X求Y" → 如"信用分配问题"
- method：有名字的可复现算法 → 如"QMIX"
- technique：方法内部的组件/技巧 → 如"注意力加权混合"

判定：五步 yes/no 排除法（见第零章）。
</taxonomy>

<task>
请构建概念树，分三步执行：

**第一步：画锚点路径**
从 paper_summary.research_context 提取 field → direction 的最短路径。
这些节点标记 "is_anchor": true，不展开子树。

**第二步：在锚点末端展开贡献子树**
从 paper_summary.core_contributions 和 novel_concepts 提取概念。
标记 "is_anchor": false。

**第三步：标注贡献类型**
对每个核心节点标注 contribution_role：
- "proposed"：论文首次提出
- "improved"：论文改进了已有方法
- "applied"：已有方法应用于新场景
- "analyzed"：对已有概念的深入分析
</task>

<confidence_scale>
| 分数 | 含义 |
|------|------|
| 0.90-1.00 | 论文明确讨论，层级无歧义 |
| 0.75-0.89 | 论文涉及，层级基本确定 |
| 0.60-0.74 | 从论文内容合理推断 |
| < 0.60 | 不要输出 |
</confidence_scale>

<output_format>
输出 JSON：

{
  "paper_summary": "one_sentence_summary 的内容",
  "concept_tree": {
    "concept": "根概念（中文）",
    "category": "field",
    "is_anchor": true,
    "children": [
      {
        "concept": "方向概念（中文）",
        "category": "direction",
        "is_anchor": true,
        "children": [
          {
            "concept": "核心贡献概念",
            "category": "subdirection|task|method|technique",
            "is_anchor": false,
            "contribution_role": "proposed|improved|applied|analyzed",
            "confidence": 0.60-1.00,
            "children": [...]
          }
        ]
      }
    ]
  },
  "methodology": "核心方法概述",
  "datasets": ["数据集"],
  "metrics": ["指标"]
}

节点数量指引：
- 锚点路径：2-4 个节点
- 贡献子树：4-10 个节点
- 总计：6-15 个。超过 15 个 → 你在提取背景而非核心。
</output_format>

只输出 JSON，不要其他内容。
```

### 1.5 效果对比

**同一篇论文（Attention-QMIX），改动前后的对比：**

#### 改动前：一阶段提取（~22 个节点）

```
人工智能 (field)
├── 机器学习 (field)                    ← 冗余层
│   ├── 强化学习 (direction)
│   │   ├── 多智能体强化学习 (direction)
│   │   │   ├── 值分解方法 (method)
│   │   │   │   ├── VDN (method)        ← 背景
│   │   │   │   ├── QMIX (method)       ← 基线，非贡献
│   │   │   │   ├── QPLEX (method)      ← 基线，非贡献
│   │   │   │   └── Attention-QMIX      ← 核心 ✓
│   │   │   ├── 策略梯度方法 (method)    ← 无关分支
│   │   │   │   └── MAPPO (method)      ← 对比基线
│   │   │   └── 通信机制 (technique)     ← 半相关
│   │   └── 单智能体强化学习 (direction) ← 完全无关
│   │       └── DQN (method)            ← 完全无关
│   └── 深度学习 (direction)            ← 完全无关
│       └── 注意力机制 (technique)       ← 工具，非贡献
```

问题：22 个节点，真正属于这篇论文贡献的只有 3-4 个。

#### 改动后：两阶段提取（8 个节点）

```
人工智能 (field, anchor)
└── 多智能体强化学习 (direction, anchor)
    ├── 值分解方法 (subdirection, improved)
    │   ├── Attention-QMIX (method, proposed)       ← 核心贡献
    │   │   ├── 注意力加权混合模块 (technique, proposed)  ← 核心贡献
    │   │   └── 单调性约束保持 (technique, applied)      ← 核心贡献
    │   └── 动态信用分配权重 (technique, proposed)       ← 核心贡献
    └── 信用分配问题 (task, analyzed)                    ← 核心贡献
```

每个节点都与论文的真正贡献直接相关。

### 1.6 代码集成建议

```python
async def process_paper(paper_content, existing_graph):
    # Stage 1: 总结（理解论文）
    summary = await call_llm(
        prompt=STAGE1_PROMPT.format(paper=paper_content),
        temperature=0.3  # 低温度追求准确
    )

    # 可选：在此处展示总结给用户确认
    # await show_summary_to_user(summary)

    # Stage 2: 提取核心（构建概念树）
    extraction = await call_llm(
        prompt=STAGE2_PROMPT.format(
            summary=summary,
            existing_graph=existing_graph
        ),
        temperature=0.2  # 更低温度，概念提取需要精确
    )
    return extraction
```

**为什么分两次调用而非合并：**

1. Stage 2 只处理 ~500 token 的摘要，而非 50000 token 的全文，提取质量更高
2. 允许用户在两阶段之间介入（修正总结后再提取）
3. Stage 1 的总结本身就是有价值的产品功能（论文摘要卡片）

**`is_anchor` 字段的前端用法：**
- anchor 节点渲染为灰色/虚线（背景定位）
- contribution 节点渲染为实色/加粗（核心贡献）
- 搜索时只匹配 contribution 节点

**`contribution_role` 字段的图谱用法：**
- proposed 节点标注"首次出现于此论文"
- improved 节点自动形成改进链（Paper A proposed X → Paper B improved X）
- 为"研究点发现"提供更丰富的信号

---

## 第二章：概念合并

### 2.1 原版问题诊断

**原文件位置**: `openclaw/dedup/analyzer.py` 第 43-104 行

| # | 问题 | 严重度 | 说明 |
|---|------|--------|------|
| 1 | 合并标准过于模糊 | 🔴 高 | "指向同一学术概念"缺乏操作性定义 |
| 2 | 不区分合并类型 | 🔴 高 | 同义词、缩写展开、粒度吸收是不同操作 |
| 3 | 示例过少 | 🟡 中 | 只有一个正例一个反例 |
| 4 | 缺少 category 冲突处理 | 🟡 中 | 两概念名似 category 不同怎么办 |
| 5 | target_id 选择无规则 | 🟡 中 | 保留哪个没有明确标准 |

### 2.2 重写方案

```
<s>
你是一位学术术语标准化专家。你的任务是判断概念对是否应该合并，并维护知识图谱的结构完整性。

核心原则：宁可不合并（保留两个独立节点），也不可错误合并（把不同概念混为一谈）。
</s>

<task>
请逐一分析以下候选概念对，判断是否应该合并。
</task>

<candidates>
{json 格式的候选概念对列表，每对包含：
  pair_id, concept1{id, text, category, paper_count, parents, children},
  concept2{id, text, category, paper_count, parents, children}, similarity
}
</candidates>

<merge_rules>
## 应该合并的三种情况

**A 类：同义表述** — 指向完全相同的概念，仅表述不同
- "强化学习" ↔ "强化学习方法" ✅
- "卷积神经网络" ↔ "CNN" ✅
- "注意力机制" ↔ "Attention 机制" ✅
- "图神经网络" ↔ "GNN" ✅

**B 类：粒度吸收** — 一方是另一方加上无实质区分意义的修饰词
- "深度学习方法" ↔ "深度学习" ✅（"方法"是冗余后缀）
- "基于 Transformer 的方法" ↔ "Transformer" ✅
- 保留更简洁的那个作为 target

**C 类：翻译对应** — 同一概念的中英文版本
- "知识蒸馏" ↔ "Knowledge Distillation" ✅（保留中文）

## 不应该合并的四种情况

**1. 上下位关系**："机器学习" ↔ "深度学习" ❌（父子关系，不是同义词）
**2. 并列关系**："强化学习" ↔ "监督学习" ❌（同级别不同方向）
**3. 粒度差异过大**："人工智能" ↔ "梯度下降" ❌（跨多个层级）
**4. 名似义不同**："图网络" ↔ "图数据库" ❌（不同领域概念）

## 保留策略（选择 target_id）

按优先级排序：
1. 保留 paper_count 更高的（被更多论文引用的）
2. 保留子节点更多的（图谱连接更丰富的）
3. 以上相同时，保留更简洁的中文名称

## category 冲突处理

- 差一级（如 direction vs subdirection）：可合并，保留更高层级的 category
- 差两级及以上（如 field vs method）：不合并，这通常说明它们是不同概念
</merge_rules>

<output_format>
输出 JSON：

{
  "merge_suggestions": [
    {
      "pair_id": 0,
      "should_merge": true,
      "merge_type": "synonym | absorption | translation",
      "target_id": "保留的概念 ID",
      "target_text": "合并后的概念名称",
      "target_category": "合并后的 category",
      "confidence": 0.60-1.00,
      "rationale": "一句话合并理由",
      "merged_parents": ["合并后父概念 ID 列表（两者并集去重）"],
      "merged_children": ["合并后子概念 ID 列表（两者并集去重）"]
    },
    {
      "pair_id": 1,
      "should_merge": false,
      "reason_type": "hierarchical | parallel | granularity | semantic",
      "rationale": "一句话不合并理由"
    }
  ]
}
</output_format>

只输出 JSON，不要其他内容。
```

#### 改进要点

| 改动 | 原版 | 新版 | 为什么 |
|------|------|------|--------|
| 合并分类型 | 只有 should_merge | synonym/absorption/translation 三类 | 不同类型的合并后续处理不同 |
| 不合并分原因 | 只有 rationale | hierarchical/parallel/granularity/semantic 四类 | 便于分析高相似度未合并的原因 |
| 保留策略 | 无 | 三级优先级规则 | target_id 选择不再随意 |
| category 冲突 | 未处理 | 差一级可合并/差两级不合并 | 消除歧义 |
| 输出增强 | 只有 target_id | 新增 target_text, target_category, merge_type | 合并后直接入库，无需二次处理 |

---

## 第三章：研究点发现

### 3.1 原版问题诊断

**原文件位置**: `backend/routes/concepts.py` 第 304-331 行

| # | 问题 | 严重度 | 说明 |
|---|------|--------|------|
| 1 | 角色定义太弱 | 🔴 高 | "学术研究顾问"没有约束思维模式 |
| 2 | 缺少分析框架 | 🔴 高 | 没告诉 LLM 从什么角度"发现"研究点 |
| 3 | 输入术语未解释 | 🟡 中 | "边缘节点"是什么？LLM 不理解图谱术语 |
| 4 | difficulty/impact 无标准 | 🟡 中 | 自由文本还是枚举？没说清楚 |
| 5 | 缺少新颖性引导 | 🟡 中 | 容易生成已有热门方向而非研究空白 |
| 6 | 输出缺少假设句式 | 🟡 中 | 研究点描述空洞，不可验证 |

### 3.2 重写方案

```
<s>
你是一位拥有 20 年经验的科研导师，擅长从知识图谱的结构特征中识别研究机会。

你发现研究点的四种方法论：
- **空白地带法**：图谱中两个本应有联系的分支之间缺少连接 → 未被探索的交叉方向
- **末端延伸法**：叶子节点代表最具体的技术 → 它们能否应用到其他分支？
- **瓶颈识别法**：某节点连接大量子节点但自身缺少兄弟节点 → 可能是领域瓶颈
- **迁移应用法**：一个分支的成熟方法 → 能否迁移到另一个问题尚未解决的分支？
</s>

<task>
基于以下知识图谱结构信息，发现 3-5 个有价值的潜在研究方向。
优先寻找**跨分支的交叉创新点**，而非已有方向的简单延伸。
</task>

<context>
## 焦点概念
- 名称：{concept['text']}
- 层级：{concept.get('category', 'unknown')}
- 关联论文数：{concept.get('paper_count', 0)}

## 上游路径（从根到当前概念的祖先链 — 学科脉络）
{json: 祖先概念列表，每个含 text 和 category}

## 下游分支（当前概念的后代 — 已有的研究细分）
{json: 后代概念列表，每个含 text、category、paper_count}

## 邻域节点（共享父节点的不同分支 — 平行研究方向）
{json: 兄弟分支概念列表}

## 远端节点（图谱中距离较远的叶子 — 潜在跨领域连接机会）
{json: 远端叶子节点列表}

## 相关论文
{json: 论文信息列表，每篇含 title 和 research_questions}
</context>

<output_format>
输出 JSON 数组，每个研究点包含：

[
  {
    "title": "研究点标题（15字以内）",
    "hypothesis": "核心假设（用'如果将 X 应用于 Y，可能解决 Z 问题'的句式）",
    "description": "详细描述（80-150字），含问题背景、方法思路、预期结果",
    "discovery_method": "gap_filling | leaf_extension | bottleneck | transfer",
    "rationale": "为什么图谱结构暗示了这个研究机会（引用具体节点关系）",
    "related_concepts": ["涉及的概念名称"],
    "difficulty": "low | medium | high",
    "difficulty_reason": "难度依据（一句话）",
    "novelty": "incremental | moderate | high",
    "potential_impact": "niche | broad | transformative"
  }
]

评分标准：

difficulty:
- low：现有方法直接扩展，3-6 个月
- medium：需新方法或新数据，6-12 个月
- high：基础理论创新或大规模实验，1 年以上

novelty:
- incremental：已有方法的小幅改进
- moderate：已有方法创造性应用于新问题
- high：新的问题定义或理论框架

potential_impact:
- niche：特定子领域的小范围影响
- broad：对整个研究方向有推动
- transformative：可能改变领域基本范式
</output_format>

只输出 JSON 数组，不要其他内容。
```

#### 改进要点

| 改动 | 原版 | 新版 | 为什么 |
|------|------|------|--------|
| 分析框架 | 无 | 四种发现方法（空白/延伸/瓶颈/迁移） | 给 LLM 结构化的思考抓手 |
| 输入语义化 | "边缘节点" | "邻域节点"+"远端节点"并解释含义 | LLM 能理解每类输入代表什么 |
| 新增 hypothesis | 无 | 强制"如果X应用于Y"句式 | 研究点可验证、可操作 |
| 新增 discovery_method | 无 | 标注发现策略 | 便于评估哪种策略最有效 |
| 新增 novelty | 无 | 区分微创新和新方向 | 避免生成"已知热门方向" |
| difficulty/impact | 自由文本 | 枚举值 + 标定标准 | 可排序、可筛选 |

---

## 附录：快速替换对照表

| 文件 | 行号 | 改动类型 | 核心变更 |
|------|------|----------|----------|
| `openclaw/pdf_parser.py` | 428-631 | **拆分为两个 prompt** | 原有的单一 prompt 拆为 Stage 1（总结）和 Stage 2（提取核心） |
| `openclaw/dedup/analyzer.py` | 43-104 | **替换** | 新增合并类型分类、不合并原因分类、保留策略优先级 |
| `backend/routes/concepts.py` | 304-331 | **替换** | 新增四种发现方法框架、hypothesis 字段、枚举化评分 |

### 新增文件建议

| 文件 | 内容 |
|------|------|
| `CLASSIFICATION.md` | 分类原则文档（第零章内容），作为所有 prompt 的理论基础 |
| `PROMPT_GUIDE.md` | 本文档本身，作为 prompt 维护的参考手册 |

### LLM 兼容性

| LLM | XML 标签 | 备注 |
|-----|----------|------|
| Claude | ✅ 最佳 | XML 标签是 Claude 的原生分区方式 |
| Gemini | ✅ 良好 | 能正确识别 XML 标签 |
| Qwen | ⚠️ 一般 | XML 效果略弱，可用 `## 标题` 替代 XML 标签 |
| DeepSeek | ✅ 良好 | 支持 XML 标签 |

如果需要兼容 Qwen，可将 `<s>...</s>` 改为 `## 角色定义\n...`，将 `<task>...</task>` 改为 `## 任务\n...`，效果差距不大。
