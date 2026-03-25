# Prompt Engineering Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optimize three core LLM prompts (concept extraction, concept merge, research points) to improve extraction quality and reduce noise in the knowledge graph.

**Architecture:**
1. Split concept extraction into two stages (summary → extraction) to distinguish background concepts from core contributions
2. Add merge type classification and not-merge reasons to concept deduplication
3. Add structured discovery framework to research point generation

**Tech Stack:** Python, FastAPI, dataclasses, LLM API clients (Anthropic/Google/OpenAI-compatible)

**Reference:** `PROMPT_GUIDE.md` contains detailed prompt specifications

---

## File Structure

| File | Responsibility |
|------|----------------|
| `openclaw/pdf_parser.py` | Concept extraction (two-stage prompts) |
| `openclaw/dedup/analyzer.py` | Concept merge analysis |
| `backend/routes/concepts.py` | Research points discovery |
| `openclaw/database.py` | Schema updates for new fields |

---

### Task 1: Update ConceptTree Dataclass with New Fields

**Files:**
- Modify: `openclaw/pdf_parser.py:32-60`

- [ ] **Step 1: Update ConceptTree dataclass to include is_anchor and contribution_role fields**

```python
@dataclass
class ConceptTree:
    """
    概念树结构

    示例结构:
    {
        "concept": "人工智能",
        "category": "field",
        "confidence": 0.95,
        "is_anchor": true,  # 新增：是否为锚点节点
        "contribution_role": null,  # 新增：proposed/improved/applied/analyzed
        "children": [...]
    }
    """
    concept: str
    category: str = "method"
    confidence: float = 0.9
    is_anchor: bool = False  # 新增
    contribution_role: Optional[str] = None  # 新增: proposed/improved/applied/analyzed
    children: List['ConceptTree'] = field(default_factory=list)

    def to_dict(self):
        result = {
            "concept": self.concept,
            "category": self.category,
            "confidence": self.confidence,
            "is_anchor": self.is_anchor,
        }
        if self.contribution_role:
            result["contribution_role"] = self.contribution_role
        if self.children:
            result["children"] = [c.to_dict() for c in self.children]
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'ConceptTree':
        return cls(
            concept=data.get('concept', ''),
            category=data.get('category', 'method'),
            confidence=data.get('confidence', 0.9),
            is_anchor=data.get('is_anchor', False),
            contribution_role=data.get('contribution_role'),
            children=[cls.from_dict(c) for c in data.get('children', [])]
        )
```

- [ ] **Step 2: Update LLMExtractedContent to include paper summary fields**

```python
@dataclass
class LLMExtractedContent:
    """LLM 提取的结构化内容"""
    title: str
    authors: List[str]
    abstract: str
    research_questions: List[str]
    contributions: List[str]
    concept_tree: ConceptTree
    methodology: Optional[str]
    datasets: List[str]
    metrics: List[str]
    # 新增 Stage 1 摘要字段
    one_sentence_summary: Optional[str] = None
    research_context: Optional[Dict] = None  # {field, direction, existing_gap}
    background_concepts: List[str] = field(default_factory=list)
    novel_concepts: List[str] = field(default_factory=list)
```

- [ ] **Step 3: Commit changes**

```bash
git add openclaw/pdf_parser.py
git commit -m "feat: add is_anchor and contribution_role fields to ConceptTree"
```

---

### Task 2: Implement Stage 1 Prompt (Paper Summary)

**Files:**
- Modify: `openclaw/pdf_parser.py:428-631`

- [ ] **Step 1: Add Stage 1 prompt constant**

```python
STAGE1_SUMMARY_PROMPT = """<s>
你是一位学术论文审稿人。请对以下论文进行结构化总结。
你的目标不是复述论文内容，而是回答一个核心问题：
**这篇论文对学术界的独特贡献是什么？它做了什么别人没做过的事？**
</s>

<paper>
<title>{title}</title>
<authors>{authors}</authors>
<abstract>{abstract}</abstract>
<body>{body}</body>
</paper>

<task>
请输出以下 JSON 结构：

{{
  "one_sentence_summary": "用一句话概括这篇论文（不超过50字）",

  "research_context": {{
    "field": "所属大领域",
    "direction": "所属研究方向",
    "existing_gap": "论文试图填补的研究空白（1-2句话）"
  }},

  "core_contributions": [
    {{
      "type": "new_method | new_framework | new_dataset | new_finding | improvement | theoretical",
      "claim": "贡献的具体描述（1句话）",
      "novelty": "与已有工作相比，新在哪里（1句话）"
    }}
  ],

  "methodology_summary": {{
    "approach": "核心方法的一句话概述",
    "key_components": ["方法中最关键的2-3个技术组件"],
    "baselines": ["对比的基线方法"]
  }},

  "results_summary": {{
    "datasets": ["使用的数据集"],
    "metrics": ["评估指标"],
    "main_finding": "最重要的实验结论（1句话）"
  }},

  "background_concepts": ["论文提及但非其贡献的已有概念"],
  "novel_concepts": ["论文首次提出或深入探讨的概念"]
}}
</task>

<rules>
关键判断规则：
- "background_concepts" vs "novel_concepts" 的区分是最重要的。
  判断标准：如果这篇论文不存在，这个概念还会被学术界广泛认知吗？
  会 → background。不会 → novel。
- core_contributions 通常只有 1-3 个。超过 5 个说明没有区分"贡献"和"论文提到的东西"。
- 所有内容使用中文。国际通用专有名词（Transformer、BERT）可保留英文。
</rules>

只输出 JSON，不要其他内容。"""
```

- [ ] **Step 2: Add _stage1_summarize method to LLMConceptExtractor**

```python
def _stage1_summarize(self, paper_content: PaperContent) -> dict:
    """
    Stage 1: 论文总结
    目标：理解论文，区分背景概念和核心贡献
    """
    prompt = STAGE1_SUMMARY_PROMPT.format(
        title=paper_content.title,
        authors=', '.join(paper_content.authors[:5]) if paper_content.authors else 'Unknown',
        abstract=paper_content.abstract[:1000] if paper_content.abstract else '',
        body=paper_content.full_text[:50000]
    )

    response = self.api_client.extract_concepts(prompt)
    return self._parse_stage1_response(response)

def _parse_stage1_response(self, response: str) -> dict:
    """解析 Stage 1 响应"""
    import json
    import re

    try:
        json_match = re.search(r'```json\s*(.+?)\s*```', response, re.DOTALL)
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
            "novel_concepts": []
        }
```

- [ ] **Step 3: Commit changes**

```bash
git add openclaw/pdf_parser.py
git commit -m "feat: add Stage 1 summary prompt for paper understanding"
```

---

### Task 3: Implement Stage 2 Prompt (Core Concept Extraction)

**Files:**
- Modify: `openclaw/pdf_parser.py`

- [ ] **Step 1: Add Stage 2 prompt constant**

```python
STAGE2_EXTRACTION_PROMPT = """<s>
你是一位学术知识图谱构建专家。你的任务是基于论文总结，构建一棵精炼的概念树。

关键原则——区分"锚点"和"贡献"：
- **锚点路径**：从根节点到论文核心贡献的最短路径。只需存在，不展开子树。作用是定位"这篇论文属于哪里"。
- **贡献子树**：论文真正贡献的概念。展开详细子节点。这些是图谱中因为这篇论文而新增的知识。
</s>

<paper_summary>
{summary_json}
</paper_summary>

{existing_graph_section}

<taxonomy>
层级定义（基于"最小可发表单元"原则）：
- field：能建大学院系 → 如"人工智能"
- direction：有专门学术会议 → 如"多智能体强化学习"
- subdirection：综述论文的独立章节 → 如"值分解方法"
- task：可表述为"给定X求Y" → 如"信用分配问题"
- method：有名字的可复现算法 → 如"QMIX"
- technique：方法内部的组件/技巧 → 如"注意力加权混合"

判定：五步 yes/no 排除法：
1. 能不能围绕它建一个大学院系？→ field
2. 有没有专门的学术会议或期刊专题？→ direction
3. 会不会在该方向的综述论文中作为独立章节？→ subdirection
4. 能不能表述成"给定X，求解/优化Y"的问题定义？→ task
5. 有没有具体名字和可复现的算法流程？→ method
6. 以上都不是 → technique
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

{{
  "paper_summary": "one_sentence_summary 的内容",
  "concept_tree": {{
    "concept": "根概念（中文）",
    "category": "field",
    "is_anchor": true,
    "children": [
      {{
        "concept": "方向概念（中文）",
        "category": "direction",
        "is_anchor": true,
        "children": [
          {{
            "concept": "核心贡献概念",
            "category": "subdirection|task|method|technique",
            "is_anchor": false,
            "contribution_role": "proposed|improved|applied|analyzed",
            "confidence": 0.60-1.00,
            "children": [...]
          }}
        ]
      }}
    ]
  }},
  "methodology": "核心方法概述",
  "datasets": ["数据集"],
  "metrics": ["指标"]
}}

节点数量指引：
- 锚点路径：2-4 个节点
- 贡献子树：4-10 个节点
- 总计：6-15 个。超过 15 个 → 你在提取背景而非核心。
</output_format>

只输出 JSON，不要其他内容。"""

EXISTING_GRAPH_SECTION = """<existing_graph>
当前知识图谱中已有的概念。请优先复用已有节点作为锚点，避免重复创建。
{existing_tree}
</existing_graph>"""
```

- [ ] **Step 2: Add _stage2_extract method to LLMConceptExtractor**

```python
def _stage2_extract(self, summary: dict, existing_concepts: str = "") -> dict:
    """
    Stage 2: 核心概念提取
    目标：基于 Stage 1 摘要，只提取核心贡献对应的概念树
    """
    # 构建已有图谱部分
    existing_section = ""
    if existing_concepts and existing_concepts != "（图谱为空）":
        existing_section = EXISTING_GRAPH_SECTION.format(existing_tree=existing_concepts)

    prompt = STAGE2_EXTRACTION_PROMPT.format(
        summary_json=json.dumps(summary, ensure_ascii=False, indent=2),
        existing_graph_section=existing_section
    )

    response = self.api_client.extract_concepts(prompt)
    return self._parse_stage2_response(response)

def _parse_stage2_response(self, response: str) -> dict:
    """解析 Stage 2 响应"""
    import json
    import re

    try:
        json_match = re.search(r'```json\s*(.+?)\s*```', response, re.DOTALL)
        json_str = json_match.group(1) if json_match else response.strip()
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Stage 2 解析失败: {e}")
        return {
            "paper_summary": "",
            "concept_tree": {},
            "methodology": "",
            "datasets": [],
            "metrics": []
        }
```

- [ ] **Step 3: Update extract method to use two-stage approach**

```python
def extract(self, paper_content: PaperContent, existing_concepts: str = "") -> LLMExtractedContent:
    """
    从论文内容提取概念树和结构化信息（两阶段架构）

    Stage 1: 论文总结 - 理解论文，区分背景和贡献
    Stage 2: 核心提取 - 基于摘要构建概念树
    """
    if not self.api_client:
        raise ValueError("需要配置 LLM API 客户端")

    # Stage 1: 总结（理解论文）
    summary = self._stage1_summarize(paper_content)

    # Stage 2: 提取核心（构建概念树）
    extraction = self._stage2_extract(summary, existing_concepts)

    # 合并结果
    concept_tree = self._build_concept_tree(extraction.get('concept_tree', {}))

    return LLMExtractedContent(
        title=summary.get('one_sentence_summary', paper_content.title),
        authors=paper_content.authors,
        abstract=paper_content.abstract,
        research_questions=[],
        contributions=[c.get('claim', '') for c in summary.get('core_contributions', [])],
        concept_tree=concept_tree,
        methodology=extraction.get('methodology'),
        datasets=extraction.get('results_summary', {}).get('datasets', []),
        metrics=extraction.get('results_summary', {}).get('metrics', []),
        # 新增字段
        one_sentence_summary=summary.get('one_sentence_summary'),
        research_context=summary.get('research_context'),
        background_concepts=summary.get('background_concepts', []),
        novel_concepts=summary.get('novel_concepts', [])
    )
```

- [ ] **Step 4: Commit changes**

```bash
git add openclaw/pdf_parser.py
git commit -m "feat: implement two-stage concept extraction (summary + core extraction)"
```

---

### Task 4: Update Concept Merge Prompt

**Files:**
- Modify: `openclaw/dedup/analyzer.py`

- [ ] **Step 1: Update MergeSuggestion dataclass**

```python
@dataclass
class MergeSuggestion:
    """合并建议"""
    source_id: str
    target_id: str
    target_text: str = ""  # 新增：合并后的概念名称
    target_category: str = ""  # 新增：合并后的 category
    merge_type: str = ""  # 新增：synonym/absorption/translation
    confidence: float = 0.8
    rationale: str = ""
    merged_relations: Dict[str, List[str]] = field(default_factory=dict)
```

- [ ] **Step 2: Replace _build_prompt method with enhanced prompt**

```python
def _build_prompt(self, candidates: List) -> str:
    """构建 LLM prompt（增强版）"""
    candidate_info = []
    for i, pair in enumerate(candidates):
        # 计算 category 层级差异
        cat1 = pair.concept1.get('category', 'method')
        cat2 = pair.concept2.get('category', 'method')

        candidate_info.append({
            "pair_id": i,
            "concept1": {
                "id": pair.concept1['id'],
                "text": pair.concept1['text'],
                "category": cat1,
                "paper_count": pair.concept1.get('paper_count', 0),
                "parents": self._get_parent_names(pair.concept1['id']),
                "children": self._get_child_names(pair.concept1['id'])
            },
            "concept2": {
                "id": pair.concept2['id'],
                "text": pair.concept2['text'],
                "category": cat2,
                "paper_count": pair.concept2.get('paper_count', 0),
                "parents": self._get_parent_names(pair.concept2['id']),
                "children": self._get_child_names(pair.concept2['id'])
            },
            "similarity": round(pair.similarity, 2)
        })

    return """<s>
你是一位学术术语标准化专家。你的任务是判断概念对是否应该合并，并维护知识图谱的结构完整性。

核心原则：宁可不合并（保留两个独立节点），也不可错误合并（把不同概念混为一谈）。
</s>

<task>
请逐一分析以下候选概念对，判断是否应该合并。
</task>

<candidates>
{candidates_json}
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

{{
  "merge_suggestions": [
    {{
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
    }},
    {{
      "pair_id": 1,
      "should_merge": false,
      "reason_type": "hierarchical | parallel | granularity | semantic",
      "rationale": "一句话不合并理由"
    }}
  ]
}}
</output_format>

只输出 JSON，不要其他内容。""".format(candidates_json=json.dumps(candidate_info, ensure_ascii=False, indent=2))
```

- [ ] **Step 3: Update _parse_response to handle new fields**

```python
def _parse_response(self, response: str, candidates: List) -> List[MergeSuggestion]:
    """解析 LLM 响应（增强版）"""
    suggestions = []
    try:
        json_match = re.search(r'```json\s*(.+?)\s*```', response, re.DOTALL)
        json_str = json_match.group(1) if json_match else response.strip()
        data = json.loads(json_str)

        for item in data.get('merge_suggestions', []):
            if not item.get('should_merge', False):
                continue

            pair_id = item.get('pair_id')
            if pair_id is None or pair_id >= len(candidates):
                continue

            pair = candidates[pair_id]
            target_id = item.get('target_id', pair.concept1['id'])
            source_id = pair.concept2['id'] if target_id == pair.concept1['id'] else pair.concept1['id']

            # 获取 target_text
            target_text = item.get('target_text', '')
            if not target_text:
                target_text = pair.concept1['text'] if target_id == pair.concept1['id'] else pair.concept2['text']

            # 获取 target_category
            target_category = item.get('target_category', '')
            if not target_category:
                target_category = pair.concept1.get('category', 'method') if target_id == pair.concept1['id'] else pair.concept2.get('category', 'method')

            suggestions.append(MergeSuggestion(
                source_id=source_id,
                target_id=target_id,
                target_text=target_text,
                target_category=target_category,
                merge_type=item.get('merge_type', 'synonym'),
                confidence=item.get('confidence', 0.8),
                rationale=item.get('rationale', ''),
                merged_relations={
                    'parents': item.get('merged_parents', []),
                    'children': item.get('merged_children', [])
                }
            ))
    except (json.JSONDecodeError, KeyError) as e:
        print(f"解析 LLM 响应失败: {e}")

    return suggestions
```

- [ ] **Step 4: Commit changes**

```bash
git add openclaw/dedup/analyzer.py
git commit -m "feat: add merge type classification and enhanced merge prompt"
```

---

### Task 5: Update Research Points Discovery Prompt

**Files:**
- Modify: `backend/routes/concepts.py:218-369`

- [ ] **Step 1: Update ResearchPointResponse model to include new fields**

```python
from pydantic import BaseModel
from typing import List, Optional, Dict

class ResearchPoint(BaseModel):
    """单个研究点"""
    title: str
    hypothesis: str  # 新增：核心假设
    description: str
    rationale: str
    related_concepts: List[str]
    discovery_method: str  # 新增：gap_filling/leaf_extension/bottleneck/transfer
    difficulty: str  # low/medium/high
    difficulty_reason: str  # 新增：难度依据
    novelty: str  # 新增：incremental/moderate/high
    potential_impact: str  # niche/broad/transformative


class ResearchPointResponse(BaseModel):
    """研究点发现响应"""
    concept_id: str
    concept_name: str
    research_points: List[ResearchPoint]
    analysis_context: dict
```

- [ ] **Step 2: Update discover_research_points function with enhanced prompt**

```python
@router.get("/{concept_id}/research-points", response_model=ResearchPointResponse)
def discover_research_points(concept_id: str):
    """
    发现研究点（增强版）

    分析流程：
    1. 追溯上游节点（父概念链）
    2. 发现下游节点及其相关性
    3. 获取邻域节点（兄弟分支）
    4. 获取远端节点（潜在跨领域连接机会）
    5. 调用LLM生成研究点建议
    """
    db = get_db()
    extractor = get_extractor()

    if not extractor:
        raise HTTPException(status_code=500, detail="LLM not configured")

    # 获取概念信息
    concept = db.get_concept(concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    # 1. 追溯上游节点（祖先链）
    ancestors = []
    current_id = concept_id
    visited = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        parents = db.get_concept_parents(current_id)
        if parents:
            ancestors.extend(parents)
            current_id = parents[0]['id']
        else:
            break

    # 2. 获取下游节点（后代）
    def get_all_descendants(node_id, max_depth=5):
        descendants = []
        queue = [(node_id, 0)]
        visited_desc = set()
        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth or current in visited_desc:
                continue
            visited_desc.add(current)
            children = db.get_concept_children(current)
            for child in children:
                if child['id'] not in visited_desc:
                    descendants.append({**child, 'depth': depth + 1})
                    queue.append((child['id'], depth + 1))
        return descendants

    descendants = get_all_descendants(concept_id)

    # 3. 获取邻域节点（兄弟分支）
    siblings = []
    parent_ids = [p['id'] for p in ancestors[:1]]  # 直接父节点
    for pid in parent_ids:
        siblings.extend(db.get_concept_children(pid))
    siblings = [s for s in siblings if s['id'] != concept_id][:10]

    # 4. 获取远端节点（叶子节点）
    all_concepts = db.get_all_concepts()
    edge_nodes = []
    for c in all_concepts:
        children = db.get_concept_children(c['id'])
        if not children and c['id'] != concept_id:
            edge_nodes.append(c)

    # 5. 获取相关论文
    papers = db.get_papers_by_concept(concept_id)
    paper_info = []
    for p in papers[:5]:
        paper_info.append({
            'title': p.get('title', ''),
            'keywords': p.get('keywords', []),
        })

    # 构建分析上下文
    context = {
        'concept': {
            'id': concept_id,
            'name': concept['text'],
            'category': concept.get('category'),
            'paper_count': concept.get('paper_count', 0)
        },
        'ancestors': [{'id': a['id'], 'name': a['text'], 'category': a.get('category')} for a in ancestors[:5]],
        'descendants': [{'id': d['id'], 'name': d['text'], 'category': d.get('category'), 'depth': d.get('depth')} for d in descendants[:10]],
        'siblings': [{'id': s['id'], 'name': s['text'], 'category': s.get('category')} for s in siblings[:10]],
        'edge_nodes': [{'id': e['id'], 'name': e['text'], 'category': e.get('category')} for e in edge_nodes[:15]],
        'related_papers': paper_info,
    }

    # 构建 prompt
    prompt = _build_research_prompt(context)

    try:
        response = extractor.api_client.generate(prompt)

        # 解析响应
        response_text = response.strip()
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])

        research_points = json.loads(response_text)

        return ResearchPointResponse(
            concept_id=concept_id,
            concept_name=concept['text'],
            research_points=research_points,
            analysis_context=context,
        )
    except json.JSONDecodeError as e:
        return ResearchPointResponse(
            concept_id=concept_id,
            concept_name=concept['text'],
            research_points=[{
                "title": "研究点分析",
                "hypothesis": "",
                "description": "LLM返回格式异常，请重试",
                "rationale": str(e),
                "related_concepts": [],
                "discovery_method": "unknown",
                "difficulty": "unknown",
                "difficulty_reason": "",
                "novelty": "unknown",
                "potential_impact": "unknown",
            }],
            analysis_context=context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM analysis failed: {str(e)}")


def _build_research_prompt(context: dict) -> str:
    """构建研究点发现 prompt（增强版）"""
    return """<s>
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
- 名称：{concept_name}
- 层级：{concept_category}
- 关联论文数：{paper_count}

## 上游路径（从根到当前概念的祖先链 — 学科脉络）
{ancestors_json}

## 下游分支（当前概念的后代 — 已有的研究细分）
{descendants_json}

## 邻域节点（共享父节点的不同分支 — 平行研究方向）
{siblings_json}

## 远端节点（图谱中距离较远的叶子 — 潜在跨领域连接机会）
{edge_nodes_json}

## 相关论文
{papers_json}
</context>

<output_format>
输出 JSON 数组，每个研究点包含：

[
  {{
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
  }}
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

只输出 JSON 数组，不要其他内容。""".format(
        concept_name=context['concept']['name'],
        concept_category=context['concept'].get('category', 'unknown'),
        paper_count=context['concept'].get('paper_count', 0),
        ancestors_json=json.dumps([a['name'] for a in context['ancestors']], ensure_ascii=False, indent=2),
        descendants_json=json.dumps([{'name': d['name'], 'depth': d.get('depth')} for d in context['descendants']], ensure_ascii=False, indent=2),
        siblings_json=json.dumps([s['name'] for s in context['siblings']], ensure_ascii=False, indent=2),
        edge_nodes_json=json.dumps([e['name'] for e in context['edge_nodes']], ensure_ascii=False, indent=2),
        papers_json=json.dumps([{'title': p['title'], 'keywords': p['keywords']} for p in context['related_papers']], ensure_ascii=False, indent=2)
    )
```

- [ ] **Step 3: Commit changes**

```bash
git add backend/routes/concepts.py
git commit -m "feat: add structured discovery framework to research points prompt"
```

---

### Task 6: Integration Testing

**Files:**
- Test: Manual testing via API

- [ ] **Step 1: Start the backend server**

```bash
cd D:/meta-knowledge-graph-main
python -m uvicorn backend.main:app --reload --port 8000
```

- [ ] **Step 2: Test concept extraction with a sample paper**

Use the `/extract-concepts` skill or manually test via the papers API endpoint.

- [ ] **Step 3: Test concept merge with the dedup panel**

Navigate to the Concepts page, click "去重扫描" button to trigger merge analysis.

- [ ] **Step 4: Test research points discovery**

Click on a concept in the graph, then click "发现研究点" button.

- [ ] **Step 5: Commit final integration**

```bash
git add -A
git commit -m "feat: complete prompt engineering optimization"
```

---

## Summary

| Task | Description | Key Changes |
|------|-------------|-------------|
| 1 | Update dataclasses | Add `is_anchor`, `contribution_role` fields |
| 2 | Stage 1 prompt | Paper summary with background/novel distinction |
| 3 | Stage 2 prompt | Core concept extraction with anchor path |
| 4 | Merge prompt | Merge type classification, category conflict handling |
| 5 | Research prompt | Four discovery methods, hypothesis field |
| 6 | Testing | Manual verification of all three features |