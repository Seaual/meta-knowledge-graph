"""LLM 概念提取器"""

from mkg.pdf_models import ConceptTree, LLMExtractedContent, PaperContent

STAGE1_SUMMARY_PROMPT = """<s>
You are a senior academic literature analyst with expertise in identifying the precise contribution boundaries of research papers. Your core skill is distinguishing what a paper actually contributed from what it merely mentioned or used as background.

Your working principles:
- Extract contributions conservatively: if unsure whether something is a contribution or background, classify it as background.
- Name concepts using the terminology the academic community would recognize, not the paper's idiosyncratic phrasing.
- Provide BOTH English and Chinese for all text fields. Keep internationally recognized terms (e.g., Transformer, BERT, GAN) in their original form.
</s>

<paper>
<title>{title}</title>
<authors>{authors}</authors>
<abstract>{abstract}</abstract>
<body>{body}</body>
</paper>

<task>
Before generating JSON, think through these questions (this reasoning will not be shown to users):

1. What is the SINGLE most important thing this paper did that didn't exist before?
2. What field and direction does this belong to?
3. Which concepts in this paper are BACKGROUND (would exist without this paper) vs NOVEL (wouldn't exist without this paper)?
4. How many real contributions does this paper have? (Usually 1-3. If you're counting more than 3, you're probably including background work.)

Then output the following JSON:

{{
  "one_sentence_summary": {{
    "en": "One sentence summary (max 50 words)",
    "zh": "一句话概括（不超过50字）"
  }},

  "research_context": {{
    "field": {{
      "en": "Major research field",
      "zh": "所属大领域"
    }},
    "direction": {{
      "en": "Specific research direction",
      "zh": "所属研究方向"
    }},
    "existing_gap": {{
      "en": "The specific gap this paper fills — what was impossible or unsolved before this paper? (1-2 sentences)",
      "zh": "这篇论文填补了什么空白——在这篇论文之前什么是做不到或未解决的？（1-2句话）"
    }}
  }},

  "core_contributions": [
    {{
      "type": "new_method | new_framework | new_dataset | new_finding | improvement | theoretical",
      "claim": {{
        "en": "What exactly did this paper contribute? (1 sentence, be specific)",
        "zh": "这篇论文具体贡献了什么？（1句话，要具体）"
      }},
      "novelty": {{
        "en": "Compared to the closest prior work, what is new? Name the prior work explicitly. (1 sentence)",
        "zh": "与最接近的已有工作相比新在哪？请明确指出已有工作的名称。（1句话）"
      }}
    }}
  ],

  "methodology_summary": {{
    "approach": {{
      "en": "Core method in one sentence",
      "zh": "核心方法一句话概述"
    }},
    "key_components": {{
      "en": ["2-3 most critical technical components (not all components, just the novel ones)"],
      "zh": ["最关键的2-3个技术组件（只列新颖的，不列标准组件）"]
    }},
    "baselines": {{
      "en": ["Baseline methods compared against"],
      "zh": ["对比的基线方法"]
    }}
  }},

  "results_summary": {{
    "datasets": {{
      "en": ["Datasets used"],
      "zh": ["使用的数据集"]
    }},
    "metrics": {{
      "en": ["Evaluation metrics"],
      "zh": ["评估指标"]
    }},
    "main_finding": {{
      "en": "Most important result WITH numbers if available (e.g., 'Outperforms QMIX by 12-18% win rate on SMAC hard scenarios')",
      "zh": "最重要的实验结论，尽量带具体数字"
    }}
  }},

  "background_concepts": {{
    "en": ["Concepts this paper USES but did NOT create — these would be well-known even if this paper didn't exist"],
    "zh": ["论文使用但并非其创造的概念——即使这篇论文不存在，这些概念也是学术界广泛认知的"]
  }},
  "novel_concepts": {{
    "en": ["Concepts that ONLY exist because of this paper — if this paper disappeared, these concepts would not be known"],
    "zh": ["因为这篇论文才存在的概念——如果这篇论文消失，这些概念就不会被人知道"]
  }}
}}
</task>

<rules>
Critical rules:

1. BACKGROUND vs NOVEL is the most important judgment in this task.
   - Baselines are ALWAYS background (e.g., QMIX, BERT, ResNet — these exist regardless of this paper)
   - Standard techniques are ALWAYS background (e.g., attention mechanism, dropout, batch normalization)
   - Only concepts NAMED and DEFINED for the first time in this paper are novel

2. core_contributions should have 1-3 items.
   - If you listed 4+, re-examine: are some of these "things the paper did" rather than "things the paper contributed"?
   - "Used dataset X" is not a contribution unless the paper CREATED dataset X.
   - "Achieved SOTA" is a result, not a contribution — the contribution is the METHOD that achieved SOTA.

3. Provide BOTH English and Chinese for all text fields.

4. If the paper is unclear or you cannot determine the contribution with confidence, say so in one_sentence_summary rather than guessing.
</rules>

Output JSON only, no other content."""


STAGE2_EXTRACTION_PROMPT = """<s>
You are an academic knowledge graph construction expert. Your task is to build a refined concept tree based on the paper summary.

Key Principle — Distinguish "anchors" from "contributions":
- **Anchor Path**: The shortest path from root to the paper's core contribution. These nodes just need to EXIST to locate the paper in the graph. Do NOT expand subtrees for anchors.
- **Contribution Subtree**: Concepts the paper truly contributed. These get full subtree expansion. These are the NEW KNOWLEDGE this paper adds to the graph.

Analogy: Anchor path is the "address" (Beijing → Haidian → Zhongguancun). Contribution subtree is "what's inside the room". You don't describe how big Beijing is — you describe what's in this specific room.

Node budget: Aim for 8-12 nodes total. More than 15 means you're extracting background, not contributions.
</s>

<paper_summary>
{summary_json}
</paper_summary>

{existing_graph_section}

<taxonomy>
Hierarchy Definition (based on "Minimum Publishable Unit" principle):

| Level | Code | Definition | Decision Rule | Examples |
|-------|------|------------|---------------|----------|
| Major field | field | An independent academic discipline | Could a university build a department around it? | AI, Operations Research |
| Direction | direction | Has its own research community | Is there a dedicated conference or journal track? | Reinforcement Learning, Object Detection |
| Subdirection | subdirection | Subdivision within a direction | Would it be an independent chapter in a survey of the parent direction? | Multi-Agent RL, Few-shot Object Detection |
| Task | task | Specific problem definition | Can you state it as "Given X, find/optimize Y"? | Credit Assignment, Domain Adaptation |
| Dataset | dataset | Named benchmark or data contribution | Is it a specific named dataset used by the community as a benchmark? | ImageNet, SMAC, HumanEval |
| Method | method | Named, reproducible algorithm | Does it have a specific name and reproducible procedure? | QMIX, YOLOv5, LoRA |
| Finding | finding | Key experimental discovery or empirical law | Is it a named result that changed how people think? | Scaling Laws, Bitter Lesson |
| Technique | technique | Component or trick within a method | None of the above → default to technique | Attention weighting, Gradient clipping |

Decision flow (ask in this order, stop at first "yes"):
1. University department? → field
2. Dedicated conference? → direction
3. Survey chapter? → subdirection
4. "Given X, find Y"? → task
5. Named benchmark dataset? → dataset
6. Named reproducible algorithm? → method
7. Named empirical discovery? → finding
8. None of above → technique

Three structural invariants:
1. **Strict monotonicity**: Parent level must be strictly higher than all children
2. **Context sensitivity**: Same term can be different levels depending on paper scope
3. **Conservative default**: When ambiguous between two adjacent levels, pick the lower (more specific) one
</taxonomy>

<task>
Build the concept tree in three steps:

**Step 1: Draw Anchor Path**
From paper_summary.research_context, extract the shortest path: field → direction.
- Mark these nodes "is_anchor": true
- Do NOT expand any children for anchor nodes
- If existing_graph has matching concepts, reuse their exact names

**Step 2: Expand Contribution Subtree**
From paper_summary.core_contributions and novel_concepts, extract the concepts this paper actually contributed.
- Mark these "is_anchor": false
- Attach them as children of the deepest anchor node
- Each contribution concept must have a category assigned using the taxonomy above
- Include datasets and findings as leaf nodes IF the paper contributed them (not if it merely used them)

**Step 3: Label Contribution Type**
For each non-anchor node, assign contribution_role:
- "proposed": First introduced by this paper (confidence should be ≥ 0.85)
- "improved": Paper modified or enhanced an existing concept (confidence ≥ 0.75)
- "applied": Paper applied an existing concept to a new domain/task (confidence ≥ 0.70)
- "analyzed": Paper provided new analysis/understanding of existing concept (confidence ≥ 0.65)

Note: contribution_role and confidence are correlated. "proposed" concepts should naturally have high confidence because the paper explicitly defines them. "analyzed" concepts may have lower confidence because the analysis boundary is fuzzy.
</task>

<confidence_scale>
| Score | Meaning | Typical Scenario |
|-------|---------|-----------------|
| 0.90-1.00 | Paper explicitly discusses, level unambiguous | Concepts in paper title, core contribution |
| 0.75-0.89 | Paper involves, level basically certain | Techniques described in methods section |
| 0.60-0.74 | Reasonably inferred from content | Implied upper-level concepts not explicitly named |
| < 0.60 | Do not output | — |
</confidence_scale>

<output_format>
{{
  "paper_summary": {{
    "en": "one_sentence_summary.en from Stage 1",
    "zh": "one_sentence_summary.zh from Stage 1"
  }},
  "concept_tree": {{
    "concept": {{
      "en": "Root concept (English)",
      "zh": "根概念（中文）"
    }},
    "category": "field",
    "is_anchor": true,
    "children": [
      {{
        "concept": {{
          "en": "Direction (English)",
          "zh": "方向（中文）"
        }},
        "category": "direction",
        "is_anchor": true,
        "children": [
          {{
            "concept": {{
              "en": "Core contribution (English)",
              "zh": "核心贡献（中文）"
            }},
            "category": "subdirection|task|dataset|method|finding|technique",
            "is_anchor": false,
            "contribution_role": "proposed|improved|applied|analyzed",
            "confidence": 0.60-1.00,
            "children": [...]
          }}
        ]
      }}
    ]
  }},
  "methodology": {{
    "en": "Core method overview",
    "zh": "核心方法概述"
  }},
  "datasets": {{
    "en": ["Datasets"],
    "zh": ["数据集"]
  }},
  "metrics": {{
    "en": ["Metrics"],
    "zh": ["指标"]
  }}
}}
</output_format>

<rules>
Final checks before outputting:
1. Count your nodes. Anchor path: 2-4 nodes. Contribution subtree: 4-10 nodes. Total: 6-15.
2. Every parent's level is strictly higher than its children's level.
3. No anchor node has children that are also anchors (anchor path is a single chain, not a tree).
4. Every non-anchor node has a contribution_role.
5. English and Chinese names are provided for ALL concepts.
6. If a concept from existing_graph matches an anchor, you used its EXACT name.
</rules>

Output JSON only, no other content."""

EXISTING_GRAPH_SECTION = """<existing_graph>
Current concept nodes in the knowledge graph.
RULES for existing graph:
1. If an anchor concept already exists in this graph, REUSE its exact name (both en and zh) — do not create a synonym.
2. If a novel concept overlaps with an existing node, still create it but note the overlap — the dedup system will handle merging later.
3. Use the existing node's category as reference, but if you believe it's wrong based on the taxonomy below, use your judgment.

{existing_tree}
</existing_graph>"""


class LLMConceptExtractor:
    """
    LLM 概念抽取器

    使用 LLM 从论文全文中提取动态层级的概念树
    """

    def __init__(self):
        """
        初始化
        """
        pass  # 使用统一的 mkg.llm 模块

    def _stage1_summarize(self, paper_content: PaperContent) -> dict:
        """
        Stage 1: 论文总结
        目标：理解论文，区分背景概念和核心贡献
        """
        from mkg.llm import generate

        prompt = STAGE1_SUMMARY_PROMPT.format(
            title=paper_content.title,
            authors=", ".join(paper_content.authors[:5]) if paper_content.authors else "Unknown",
            abstract=paper_content.abstract[:1000] if paper_content.abstract else "",
            body=paper_content.full_text[:50000],
        )

        response = generate(
            prompt=prompt,
            system_prompt="You are a senior academic literature analyst with expertise in identifying the precise contribution boundaries of research papers.",
        )
        return self._parse_stage1_response(response)

    def _parse_stage1_response(self, response: str) -> dict:
        """解析 Stage 1 响应"""
        import json
        import re

        try:
            json_match = re.search(r"```json\s*(.+?)\s*```", response, re.DOTALL)
            json_str = json_match.group(1) if json_match else response.strip()
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Stage 1 解析失败: {e}")
            return {
                "one_sentence_summary": "",
                "research_context": {},
                "core_contributions": [],
                "methodology_summary": {},
                "results_summary": {},
                "background_concepts": [],
                "novel_concepts": [],
            }

    def _stage2_extract(self, summary: dict, existing_concepts: str = "") -> dict:
        """
        Stage 2: 核心概念提取
        目标：基于 Stage 1 摘要，只提取核心贡献对应的概念树
        """
        import json

        from mkg.llm import generate

        # 构建已有图谱部分
        existing_section = ""
        if existing_concepts and existing_concepts != "（图谱为空）":
            existing_section = EXISTING_GRAPH_SECTION.format(existing_tree=existing_concepts)

        prompt = STAGE2_EXTRACTION_PROMPT.format(
            summary_json=json.dumps(summary, ensure_ascii=False, indent=2), existing_graph_section=existing_section
        )

        response = generate(
            prompt=prompt,
            system_prompt="You are an academic knowledge graph construction expert. Build a refined concept tree based on the paper summary.",
        )
        return self._parse_stage2_response(response)

    def _parse_stage2_response(self, response: str) -> dict:
        """解析 Stage 2 响应"""
        import json
        import re

        try:
            json_match = re.search(r"```json\s*(.+?)\s*```", response, re.DOTALL)
            json_str = json_match.group(1) if json_match else response.strip()
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Stage 2 解析失败: {e}")
            return {"paper_summary": "", "concept_tree": {}, "methodology": "", "datasets": [], "metrics": []}

    def extract(self, paper_content: PaperContent, existing_concepts: str = "") -> LLMExtractedContent:
        """
        从论文内容提取概念树和结构化信息（两阶段架构）

        Stage 1: 论文总结 - 理解论文，区分背景和贡献
        Stage 2: 核心提取 - 基于摘要构建概念树
        """
        # Stage 1: 总结（理解论文）
        summary = self._stage1_summarize(paper_content)

        # Stage 2: 提取核心（构建概念树）
        extraction = self._stage2_extract(summary, existing_concepts)

        # 合并结果
        concept_tree = self._build_concept_tree(extraction.get("concept_tree", {}))

        # 获取 results_summary 中的数据集和指标
        results_summary = summary.get("results_summary", {})

        return LLMExtractedContent(
            title=summary.get("one_sentence_summary", paper_content.title),
            authors=paper_content.authors,
            abstract=paper_content.abstract,
            research_questions=[],
            contributions=[c.get("claim", "") for c in summary.get("core_contributions", [])],
            concept_tree=concept_tree,
            methodology=extraction.get("methodology"),
            datasets=results_summary.get("datasets", []),
            metrics=results_summary.get("metrics", []),
            raw_response="",  # Two-stage extraction doesn't preserve raw response
            # 新增字段
            one_sentence_summary=summary.get("one_sentence_summary"),
            research_context=summary.get("research_context"),
            background_concepts=summary.get("background_concepts", []),
            novel_concepts=summary.get("novel_concepts", []),
        )

    def _build_extraction_prompt(self, paper_content: PaperContent, existing_concepts: str = "") -> str:
        """
        构建概念提取 Prompt（优化版）

        核心设计：
        - 让 LLM 理解论文的层次结构
        - 提取概念间的包含关系（父子关系）
        - 支持多标签归属
        - 包含清晰的判断标准、few-shot 示例和自检清单
        - 支持已有概念上下文，实现智能概念匹配
        """
        return f"""
你是一名学术知识图谱构建助手。请从这篇论文中提取概念层级结构和研究信息。

**重要：所有概念名称必须使用中文！**

## 论文信息
标题：{paper_content.title}
作者：{", ".join(paper_content.authors[:3]) if paper_content.authors else "Unknown"}
摘要：{paper_content.abstract[:500]}...

## 论文全文
{paper_content.full_text[:50000]}

{self._build_existing_concepts_section(existing_concepts)}

---

## 第一部分：层级判断标准

在提取概念时，请严格按照以下标准判断概念所属层级：

| 层级 | 英文名 | 判断标准 | 典型示例 |
|------|--------|----------|----------|
| **领域** | field | 一个广泛的学科领域，通常是一个完整的研究方向或学科分支 | 人工智能、机器学习、计算机视觉、自然语言处理 |
| **方向** | direction | 领域内的具体研究方向，通常有独立的研究社区和会议 | 强化学习、目标检测、图神经网络、知识图谱 |
| **方法** | method | 解决特定问题的具体方法或算法框架，有明确的技术路线 | Transformer、PPO算法、YOLO、BERT |
| **技术** | technique | 实现方法的具体技术手段、技巧或组件 | 注意力机制、梯度裁剪、残差连接、位置编码 |
| **细节** | detail | 算法的具体实现细节、超参数或设计选择 | 学习率0.001、3层MLP、隐藏维度256 |

**判断口诀：**
- 能独立成为一门课的 → field
- 能独立发论文的方向 → direction
- 有名字的方法框架 → method
- 方法里的具体技巧 → technique
- 数字和参数配置 → detail

---

## 第二部分：Few-shot 示例

以下是正确提取的示例（假设论文是关于多智能体强化学习的）：

**输入论文概要：** 论文提出了一个名为"Attention-QMIX"的新算法，用于解决多智能体协作问题...

**正确输出：**
```json
{{
    "title": "Attention-QMIX: 基于注意力机制的多智能体强化学习算法",
    "authors": ["张三", "李四"],
    "abstract": "摘要内容...",
    "research_questions": [
        "如何解决多智能体协作中的信用分配问题",
        "如何处理大规模智能体环境下的可扩展性"
    ],
    "contributions": [
        "提出了一种新的注意力机制用于智能体间通信",
        "在SMAC基准测试上取得了SOTA性能"
    ],
    "concept_tree": {{
        "concept": "人工智能",
        "category": "field",
        "confidence": 0.98,
        "children": [
            {{
                "concept": "机器学习",
                "category": "field",
                "confidence": 0.95,
                "children": [
                    {{
                        "concept": "强化学习",
                        "category": "direction",
                        "confidence": 0.95,
                        "children": [
                            {{
                                "concept": "多智能体强化学习",
                                "category": "direction",
                                "confidence": 0.92,
                                "children": [
                                    {{
                                        "concept": "值分解方法",
                                        "category": "method",
                                        "confidence": 0.88,
                                        "children": [
                                            {{
                                                "concept": "QMIX算法",
                                                "category": "method",
                                                "confidence": 0.85,
                                                "children": []
                                            }},
                                            {{
                                                "concept": "注意力机制",
                                                "category": "technique",
                                                "confidence": 0.82,
                                                "children": []
                                            }}
                                        ]
                                    }}
                                ]
                            }}
                        ]
                    }}
                ]
            }}
        ]
    }},
    "methodology": "采用值分解框架结合注意力机制，通过Q值混合网络实现协作决策",
    "datasets": ["SMAC", "Google Research Football"],
    "metrics": ["胜率", "平均回报", "样本效率"]
}}
```

**常见错误示例：**
❌ 错误：把"强化学习"标为 method → 应该是 direction（有独立研究社区）
❌ 错误：把"注意力机制"标为 direction → 应该是 technique（是实现技巧）
❌ 错误：概念名保留英文"Transformer" → 应翻译为"Transformer"（专有名词可保留）或"变换器"

---

## 第三部分：任务要求

### 1. 提取研究问题（1-3 个）
论文试图解决什么核心问题？用简洁的中文表述。

### 2. 提取主要贡献（1-5 个）
论文的创新点是什么？聚焦于方法、理论或实验上的贡献。

### 3. 构建概念层级树（核心任务）
从论文中提取概念，并组织成树状层级结构。

**构建原则：**
- 根节点应该是宏观研究领域（如"人工智能"、"计算机科学"）
- 按照领域→方向→方法→技术→细节的层次展开
- 每个节点的 confidence 表示提取的置信度（0-1）
- 同一概念可以出现在不同分支下（如果论文涉及多个方向）
- **所有概念名称必须翻译成中文**（专有名词如Transformer可保留）

### 4. 提取方法论
论文使用的核心方法是什么？用1-2句话概述。

### 5. 提取数据集
论文使用了哪些数据集或实验环境？

### 6. 提取评估指标
论文使用了哪些评估指标？

---

## 第四部分：输出格式

请严格按照以下 JSON 格式输出：

```json
{{
    "title": "论文标题",
    "authors": ["作者1", "作者2"],
    "abstract": "摘要...",
    "research_questions": ["问题1", "问题2"],
    "contributions": ["贡献1", "贡献2"],
    "concept_tree": {{
        "concept": "根概念（中文）",
        "category": "field",
        "confidence": 0.95,
        "children": [
            {{
                "concept": "子概念（中文）",
                "category": "direction",
                "confidence": 0.9,
                "children": [...]
            }}
        ]
    }},
    "methodology": "方法描述",
    "datasets": ["数据集1", "数据集2"],
    "metrics": ["指标1", "指标2"]
}}
```

---

## 第五部分：自检清单

在输出前，请检查以下几点：

✓ **层级正确性**：每个概念的 category 是否符合判断标准？
✓ **层级一致性**：父节点的层级是否比子节点更宏观？（field > direction > method > technique > detail）
✓ **中文翻译**：是否所有概念都已翻译成中文？
✓ **置信度合理**：confidence 是否反映了提取的确定性？
✓ **树结构完整**：concept_tree 是否有合理的根节点和层级深度？

---

**只输出 JSON，不要其他内容。开始提取！**
"""

    def _build_existing_concepts_section(self, existing_concepts: str) -> str:
        """构建已有概念参考部分"""
        if not existing_concepts or existing_concepts == "（图谱为空）":
            return ""

        return f"""---

## 已有概念树（参考）

当前知识图谱中已有以下概念结构，新概念请尽量归类到合适的位置：

{existing_concepts}

**重要规则：**
1. 如果新提取的概念已存在于上述树中，请使用相同的概念名和正确的父节点路径
2. 如果新概念是已有概念的子概念，请放在正确位置（如"卷积神经网络"应放在"人工智能→机器学习→深度学习"下）
3. 只有当概念确实是新的研究领域时，才创建新的根概念
"""

    def _parse_response(self, response: str, original_content: PaperContent) -> LLMExtractedContent:
        """解析 LLM 响应"""
        import json
        import re

        try:
            # 尝试提取 JSON（可能包含在代码块中）
            json_match = re.search(r"```json\s*(.+?)\s*```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = response.strip()

            data = json.loads(json_str)

            # 构建概念树
            concept_tree = self._build_concept_tree(data.get("concept_tree", {}))

            return LLMExtractedContent(
                title=data.get("title", original_content.title),
                authors=data.get("authors", original_content.authors),
                abstract=data.get("abstract", original_content.abstract),
                research_questions=data.get("research_questions", []),
                contributions=data.get("contributions", []),
                concept_tree=concept_tree,
                methodology=data.get("methodology"),
                datasets=data.get("datasets", []),
                metrics=data.get("metrics", []),
                raw_response=response,
            )

        except Exception as e:
            print(f"解析 LLM 响应失败：{e}")
            # 回退到基础解析
            return LLMExtractedContent(
                title=original_content.title,
                authors=original_content.authors,
                abstract=original_content.abstract,
                research_questions=[],
                contributions=[],
                concept_tree=self._create_fallback_concept_tree(original_content),
                methodology=None,
                datasets=[],
                metrics=[],
                raw_response=response,
            )

    def _build_concept_tree(self, data: dict) -> ConceptTree:
        """递归构建概念树（支持双语格式）"""
        if not data or "concept" not in data:
            return None

        # 使用 from_dict 方法处理双语格式
        return ConceptTree.from_dict(data)

    def _create_fallback_concept_tree(self, content: PaperContent) -> ConceptTree:
        """回退方案：从标题和摘要创建简单的概念树"""
        import re

        # 从标题提取关键词
        keywords = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", content.title)
        keywords = [k.lower() for k in keywords if len(k) > 3]

        # 创建扁平结构
        root = ConceptTree(concept="Research", category="field", confidence=0.5)

        for kw in keywords[:5]:
            root.children.append(ConceptTree(concept=kw, category="method", confidence=0.5))

        return root
