# mkg/agent/nodes/hypothesis_node.py
"""
研究假设生成节点

基于 4 种方法论自动生成可测试的研究假设：
- gap_filling: 填补空白
- leaf_extension: 叶子延伸
- bottleneck_breakthrough: 瓶颈突破
- migration_application: 迁移应用
"""

import json
import re
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage

from mkg.llm import get_llm_or_raise

# ============================================================
# 数据模型
# ============================================================


@dataclass
class ResearchHypothesis:
    """研究假设"""

    title: str = ""
    hypothesis: str = ""
    methodology: str = ""
    novelty_score: float = 0.5
    feasibility_score: float = 0.5
    required_methods: list[str] = field(default_factory=list)
    required_datasets: list[str] = field(default_factory=list)
    description: str = ""
    risks: list[str] = field(default_factory=list)

    @property
    def composite_score(self) -> float:
        return 0.6 * self.novelty_score + 0.4 * self.feasibility_score

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "title": self.title,
            "hypothesis": self.hypothesis,
            "methodology": self.methodology,
            "novelty_score": self.novelty_score,
            "feasibility_score": self.feasibility_score,
            "composite_score": self.composite_score,
            "required_methods": self.required_methods,
            "required_datasets": self.required_datasets,
            "description": self.description,
            "risks": self.risks,
        }


# ============================================================
# 4 种方法论配置
# ============================================================

METHODOLOGY_CONFIGS: dict[str, dict] = {
    "gap_filling": {
        "name": "填补空白",
        "description": "发现知识图谱中未被探索的概念组合",
        "prompt_template": """你是一个研究假设生成专家。请基于以下概念上下文，使用"填补空白"方法论生成可测试的研究假设。

方法论：填补空白（Gap Filling）
- 分析概念图谱中缺少连接或关系稀疏的区域
- 发现尚未被研究的子领域交叉点
- 提出连接两个独立研究方向的假设

概念上下文：
{concept_context}

要求：
1. 假设必须具体、可测试
2. 说明为什么这是一个研究空白
3. 评估创新性（0-1）和可行性（0-1）
4. 列出需要的方法和数据集

请返回 JSON 数组，每个假设包含以下字段：
- title: 假设标题（20字以内）
- hypothesis: 假设描述（100字以内，明确说明预期关系或效果）
- description: 详细说明（为什么是空白，预期贡献，200字以内）
- novelty_score: 创新性评分（0-1）
- feasibility_score: 可行性评分（0-1）
- required_methods: 所需研究方法列表
- required_datasets: 所需数据集列表
- risks: 潜在风险列表

返回 {max_count} 个假设，用 JSON 数组格式，不要返回其他内容。""",
    },
    "leaf_extension": {
        "name": "叶子延伸",
        "description": "从最具体的概念（叶子节点）向外扩展",
        "prompt_template": """你是一个研究假设生成专家。请基于以下概念上下文，使用"叶子延伸"方法论生成可测试的研究假设。

方法论：叶子延伸（Leaf Extension）
- 找到概念树中最具体的叶子节点（depth 最大的概念）
- 从叶子节点向相邻概念延伸
- 提出深化或细化现有研究的假设

概念上下文：
{concept_context}

要求：
1. 假设必须从现有叶子节点出发
2. 说明延伸方向和预期发现
3. 评估创新性（0-1）和可行性（0-1）
4. 列出需要的方法和数据集

请返回 JSON 数组，每个假设包含以下字段：
- title: 假设标题（20字以内）
- hypothesis: 假设描述（100字以内）
- description: 详细说明（从哪个叶子延伸，延伸方向，预期贡献，200字以内）
- novelty_score: 创新性评分（0-1）
- feasibility_score: 可行性评分（0-1）
- required_methods: 所需研究方法列表
- required_datasets: 所需数据集列表
- risks: 潜在风险列表

返回 {max_count} 个假设，用 JSON 数组格式，不要返回其他内容。""",
    },
    "bottleneck_breakthrough": {
        "name": "瓶颈突破",
        "description": "识别研究中的共性瓶颈并提出新方案",
        "prompt_template": """你是一个研究假设生成专家。请基于以下概念上下文，使用"瓶颈突破"方法论生成可测试的研究假设。

方法论：瓶颈突破（Bottleneck Breakthrough）
- 分析当前研究方向中的共性挑战和技术瓶颈
- 识别多篇论文都提到的局限性
- 提出绕过或突破瓶颈的新方法假设

概念上下文：
{concept_context}

要求：
1. 明确指出当前研究的瓶颈
2. 假设必须提出突破该瓶颈的新思路
3. 评估创新性（0-1）和可行性（0-1）
4. 列出需要的方法和数据集

请返回 JSON 数组，每个假设包含以下字段：
- title: 假设标题（20字以内）
- hypothesis: 假设描述（100字以内）
- description: 详细说明（当前瓶颈是什么，如何突破，预期贡献，200字以内）
- novelty_score: 创新性评分（0-1）
- feasibility_score: 可行性评分（0-1）
- required_methods: 所需研究方法列表
- required_datasets: 所需数据集列表
- risks: 潜在风险列表

返回 {max_count} 个假设，用 JSON 数组格式，不要返回其他内容。""",
    },
    "migration_application": {
        "name": "迁移应用",
        "description": "将成熟方法迁移到新的研究领域",
        "prompt_template": """你是一个研究假设生成专家。请基于以下概念上下文，使用"迁移应用"方法论生成可测试的研究假设。

方法论：迁移应用（Migration Application）
- 发现在 A 领域成熟但在 B 领域未应用的方法
- 提出方法跨领域迁移的研究假设
- 分析迁移后可能面临的适配挑战和新发现

概念上下文：
{concept_context}

要求：
1. 明确指出源领域和目标领域
2. 说明迁移的合理性和预期适应问题
3. 评估创新性（0-1）和可行性（0-1）
4. 列出需要的方法和数据集

请返回 JSON 数组，每个假设包含以下字段：
- title: 假设标题（20字以内）
- hypothesis: 假设描述（100字以内）
- description: 详细说明（源领域方法，目标领域，迁移挑战，预期贡献，200字以内）
- novelty_score: 创新性评分（0-1）
- feasibility_score: 可行性评分（0-1）
- required_methods: 所需研究方法列表
- required_datasets: 所需数据集列表
- risks: 潜在风险列表

返回 {max_count} 个假设，用 JSON 数组格式，不要返回其他内容。""",
    },
}


# ============================================================
# 假设生成器
# ============================================================


class HypothesisGenerator:
    """基于方法论的研究假设生成器"""

    def __init__(self, db=None):
        """
        Args:
            db: Database 实例
        """
        self._db = db

    def generate_hypotheses(
        self,
        concept_id: str,
        methodology: str = "all",
        max_per_method: int = 3,
    ) -> list[ResearchHypothesis]:
        """
        生成研究假设（自动从数据库获取概念上下文）

        Args:
            concept_id: 概念 ID
            methodology: 方法论类型，"all" 表示使用所有方法
            max_per_method: 每种方法生成的最大假设数

        Returns:
            按综合评分降序排列的假设列表
        """
        if not self._db:
            raise ValueError("数据库未初始化")

        # 自动构建概念上下文
        concept = self._db.get_concept(concept_id)
        if not concept:
            raise ValueError(f"未找到概念: {concept_id}")

        children = self._db.get_concept_children(concept_id) or []
        parents = self._db.get_concept_parents(concept_id) or []
        related_papers = self._db.get_papers_by_concept(concept_id) or []

        concept_context = {
            "concept": concept,
            "parents": parents[:5],
            "children": children[:15],
            "related_papers": related_papers[:10],
        }

        if methodology != "all":
            if methodology not in METHODOLOGY_CONFIGS:
                raise ValueError(f"未知的方法论: {methodology}，可选: {list(METHODOLOGY_CONFIGS.keys())}")
            methods_to_use = [methodology]
        else:
            methods_to_use = list(METHODOLOGY_CONFIGS.keys())

        all_hypotheses: list[ResearchHypothesis] = []

        for method_key in methods_to_use:
            config = METHODOLOGY_CONFIGS[method_key]
            hypotheses = self._generate_with_method(method_key, config, concept_context, max_per_method)
            all_hypotheses.extend(hypotheses)

        # 按综合评分降序
        all_hypotheses.sort(key=lambda h: h.composite_score, reverse=True)
        return all_hypotheses

    def _generate_with_method(
        self,
        method_key: str,
        config: dict,
        concept_context: dict,
        max_count: int,
    ) -> list[ResearchHypothesis]:
        """使用指定方法论生成假设"""
        context_text = self._format_context(concept_context)
        prompt = config["prompt_template"].format(
            concept_context=context_text,
            max_count=max_count,
        )

        llm = get_llm_or_raise()
        system_prompt = "你是一个专业的研究假设生成专家。请严格按照要求的 JSON 格式返回假设。"

        try:
            response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
            content = self._extract_text(response.content)
            return self._parse_json_response(content, method_key)
        except Exception as e:
            # 返回空列表，不阻断其他方法
            return []

    def _parse_json_response(self, content: str, method_key: str) -> list[ResearchHypothesis]:
        """解析 LLM 的 JSON 输出"""
        # 移除 markdown 代码块标记
        text = content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # 去掉开头的 ```json 和结尾的 ```
            start = 1
            end = len(lines) if lines[-1].strip() != "```" else len(lines) - 1
            text = "\n".join(lines[start:end]).strip()

        # 尝试解析 JSON
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # 尝试找到第一个 [ 到最后一个 ] 之间的内容
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    return []
            else:
                return []

        if not isinstance(data, list):
            return []

        hypotheses = []
        for item in data:
            try:
                h = ResearchHypothesis(
                    title=item.get("title", ""),
                    hypothesis=item.get("hypothesis", ""),
                    methodology=method_key,
                    novelty_score=float(item.get("novelty_score", 0.5)),
                    feasibility_score=float(item.get("feasibility_score", 0.5)),
                    required_methods=item.get("required_methods", []),
                    required_datasets=item.get("required_datasets", []),
                    description=item.get("description", ""),
                    risks=item.get("risks", []),
                )
                # 确保分数在 0-1 之间
                h.novelty_score = max(0.0, min(1.0, h.novelty_score))
                h.feasibility_score = max(0.0, min(1.0, h.feasibility_score))
                hypotheses.append(h)
            except (KeyError, TypeError, ValueError):
                continue

        return hypotheses

    @staticmethod
    def _format_context(context: dict) -> str:
        """格式化概念上下文为文本"""
        parts = []

        concept = context.get("concept", {})
        if concept:
            parts.append(f"核心概念: {concept.get('text', '')} (类别: {concept.get('category', '')})")
            if concept.get("description"):
                parts.append(f"描述: {concept['description']}")

        parents = context.get("parents", [])
        if parents:
            parent_names = [p.get("text", "") for p in parents]
            parts.append(f"父概念: {' -> '.join(parent_names)}")

        children = context.get("children", [])
        if children:
            child_names = [c.get("text", "") for c in children]
            parts.append(f"子概念: {', '.join(child_names)}")

        papers = context.get("related_papers", [])
        if papers:
            paper_titles = [p.get("title", "") for p in papers[:5]]
            parts.append(f"相关论文 ({len(papers)}篇):")
            for i, title in enumerate(paper_titles, 1):
                parts.append(f"  {i}. {title}")

        findings = context.get("findings", [])
        if findings:
            parts.append(f"研究发现:")
            for f in findings[:5]:
                parts.append(f"  - {f}")

        return "\n".join(parts) if parts else "暂无详细上下文"

    @staticmethod
    def _extract_text(content) -> str:
        """从 LLM 响应中提取文本"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
            return "".join(parts)
        return str(content)


# ============================================================
# 假设评审
# ============================================================


def review_hypothesis(hypothesis: dict, concept_context: dict) -> dict:
    """
    多 Agent 评审研究假设

    从 3 个维度评审：创新性、方法论合理性、潜在影响力

    Args:
        hypothesis: 假设字典
        concept_context: 概念上下文

    Returns:
        评审报告字典
    """
    llm = get_llm_or_raise()

    prompt = f"""你是学术论文评审专家。请从以下 3 个维度评审这个研究假设：

1. 创新性：假设是否提出了新的研究问题或视角？
2. 方法论合理性：提出的研究方法是否可行？
3. 潜在影响力：如果假设成立，对该领域的贡献有多大？

研究假设：
标题: {hypothesis.get('title', '')}
内容: {hypothesis.get('hypothesis', '')}
方法论: {hypothesis.get('methodology', '')}
创新性评分: {hypothesis.get('novelty_score', 'N/A')}
可行性评分: {hypothesis.get('feasibility_score', 'N/A')}

概念上下文：
{_format_review_context(concept_context)}

请返回 JSON 格式，包含以下字段：
- innovation_score: 创新性评分（0-100）
- methodology_score: 方法论合理性评分（0-100）
- impact_score: 潜在影响力评分（0-100）
- overall_score: 综合评分（0-100）
- recommendation: 评审结论（"accept" / "revise" / "reject"）
- strengths: 优势列表
- weaknesses: 弱点列表
- suggestions: 改进建议列表
- overall_comment: 总体评价（100字以内）

只返回 JSON，不要其他内容。"""

    system_prompt = "你是严格的学术论文评审专家，只返回 JSON 格式的评审结果。"

    try:
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
        content = _extract_review_text(response.content)

        # 解析 JSON
        text = content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            start = 1
            end = len(lines) if lines[-1].strip() != "```" else len(lines) - 1
            text = "\n".join(lines[start:end]).strip()

        review = json.loads(text)
        return review
    except Exception as e:
        return {
            "innovation_score": 50,
            "methodology_score": 50,
            "impact_score": 50,
            "overall_score": 50,
            "recommendation": "revise",
            "strengths": ["自动评审失败，使用默认评分"],
            "weaknesses": [],
            "suggestions": ["建议人工评审"],
            "overall_comment": f"自动评审失败: {str(e)}",
        }


def _format_review_context(context: dict) -> str:
    """格式化概念上下文用于评审"""
    parts = []

    concept = context.get("concept", {})
    if concept:
        parts.append(f"概念: {concept.get('text', '')} ({concept.get('category', '')})")
        if concept.get("description"):
            parts.append(f"描述: {concept['description']}")

    parents = context.get("parents", [])
    if parents:
        parts.append(f"上层概念: {' -> '.join(p.get('text', '') for p in parents)}")

    children = context.get("children", [])
    if children:
        parts.append(f"下层概念: {', '.join(c.get('text', '') for c in children[:5])}")

    papers = context.get("related_papers", [])
    if papers:
        parts.append(f"相关论文: {len(papers)} 篇")

    return "\n".join(parts) if parts else "暂无上下文"


def _extract_review_text(content) -> str:
    """从评审响应中提取文本"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)
