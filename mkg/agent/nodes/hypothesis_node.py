# mkg/agent/nodes/hypothesis_node.py
"""
假设生成节点 - MKG 自演化研究的核心

基于知识图谱的 4 种方法论自动生成可测试的研究假设：
1. 填补空白 - 相关分支间缺失的连接
2. 叶子延伸 - 叶子节点技术应用到其他分支
3. 瓶颈突破 - 子节点多但兄弟节点少的瓶颈
4. 迁移应用 - 成熟方法迁移到未解决的问题
"""

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage

from mkg.llm import get_llm_or_raise


# ============================================================
# 4 种研究方法论的 Prompt 模板
# ============================================================

METHODOLOGY_CONFIGS = {
    "gap_filling": {
        "name": "填补空白",
        "description": "分析概念树中两个相关分支之间缺失的连接，提出填补空白的假设",
        "prompt_template": """你是学术研究专家。基于以下知识图谱结构，使用「填补空白」方法论生成研究假设。

## 概念结构
目标概念：{concept_name} (类别: {concept_category})
父概念：{parent_concepts}
子概念：{child_concepts}
兄弟概念：{sibling_concepts}

## 相关论文
{related_papers_info}

## 方法论：填补空白
分析上述概念树，找出两个相关分支之间缺失的连接。
例如：
- 分支 A 使用了方法 X，分支 B 使用了方法 Y，但没有人尝试用 X 解决 B 的问题
- 概念 A 和概念 B 有共同的父概念，但它们之间没有交叉研究

## 任务
生成 2-3 个基于填补空白方法论的研究假设。

每个假设必须包含：
1. title: 简洁的假设标题
2. hypothesis: 完整的研究假设描述（具体、可测试）
3. gap_analysis: 分析填补了什么空白（哪些分支之间缺失连接）
4. novelty_score: 新颖性评分 (0-1)
5. feasibility_score: 可行性评分 (0-1)
6. required_methods: 需要的方法列表
7. required_datasets: 需要的数据集列表

以 JSON 数组格式返回。"""
    },
    "leaf_extension": {
        "name": "叶子延伸",
        "description": "将叶子节点（具体技术）应用到其他分支的问题上",
        "prompt_template": """你是学术研究专家。基于以下知识图谱结构，使用「叶子延伸」方法论生成研究假设。

## 概念结构
目标概念：{concept_name} (类别: {concept_category})
父概念：{parent_concepts}
子概念：{child_concepts}
兄弟概念：{sibling_concepts}

## 相关论文
{related_papers_info}

## 方法论：叶子延伸
叶子节点（最底层的具体技术/方法）往往是最成熟的。将叶子节点的技术应用到其他分支的问题上。
例如：
- 分支 A 的叶子技术 "注意力机制" 应用到分支 B 的 "时间序列预测" 问题上
- 某领域的成熟算法迁移到另一个领域

## 任务
生成 2-3 个基于叶子延伸方法论的研究假设。

每个假设必须包含：
1. title: 简洁的假设标题
2. hypothesis: 完整的研究假设描述
3. leaf_method: 被延伸的叶子技术（来源分支）
4. target_problem: 目标问题（目标分支）
5. novelty_score: 新颖性评分 (0-1)
6. feasibility_score: 可行性评分 (0-1)
7. required_methods: 需要的方法列表
8. required_datasets: 需要的数据集列表

以 JSON 数组格式返回。"""
    },
    "bottleneck_breakthrough": {
        "name": "瓶颈突破",
        "description": "识别子节点多但兄弟节点少的瓶颈节点，提出突破方案",
        "prompt_template": """你是学术研究专家。基于以下知识图谱结构，使用「瓶颈突破」方法论生成研究假设。

## 概念结构
目标概念：{concept_name} (类别: {concept_category})
父概念：{parent_concepts}
子概念：{child_concepts}
兄弟概念：{sibling_concepts}

## 相关论文
{related_papers_info}

## 方法论：瓶颈突破
识别图谱中子节点多但兄弟节点少的瓶颈节点。这些节点代表研究集中但缺乏替代方案的方向。
例如：
- 某个问题只有一种主流方法，缺乏其他方法尝试
- 某个方向研究很多，但关键瓶颈一直未解决

## 任务
生成 2-3 个基于瓶颈突破方法论的研究假设。

每个假设必须包含：
1. title: 简洁的假设标题
2. hypothesis: 完整的研究假设描述
3. bottleneck: 识别的瓶颈是什么
4. breakthrough_idea: 突破思路
5. novelty_score: 新颖性评分 (0-1)
6. feasibility_score: 可行性评分 (0-1)
7. required_methods: 需要的方法列表
8. required_datasets: 需要的数据集列表

以 JSON 数组格式返回。"""
    },
    "transfer_application": {
        "name": "迁移应用",
        "description": "将成熟方法迁移到未解决的问题上",
        "prompt_template": """你是学术研究专家。基于以下知识图谱结构，使用「迁移应用」方法论生成研究假设。

## 概念结构
目标概念：{concept_name} (类别: {concept_category})
父概念：{parent_concepts}
子概念：{child_concepts}
兄弟概念：{sibling_concepts}

## 相关论文
{related_papers_info}

## 方法论：迁移应用
将一个领域成熟的方法迁移到另一个未解决的问题上。
例如：
- 图神经网络从社交网络分析迁移到药物发现
- Transformer 从 NLP 迁移到时间序列预测

## 任务
生成 2-3 个基于迁移应用方法论的研究假设。

每个假设必须包含：
1. title: 简洁的假设标题
2. hypothesis: 完整的研究假设描述
3. source_domain: 方法来源领域
4. target_domain: 方法目标领域
5. novelty_score: 新颖性评分 (0-1)
6. feasibility_score: 可行性评分 (0-1)
7. required_methods: 需要的方法列表
8. required_datasets: 需要的数据集列表

以 JSON 数组格式返回。"""
    }
}


# ============================================================
# 假设数据模型
# ============================================================

class ResearchHypothesis:
    """研究假设"""
    
    def __init__(
        self,
        title: str,
        hypothesis: str,
        methodology: str,
        novelty_score: float,
        feasibility_score: float,
        required_methods: list[str] | None = None,
        required_datasets: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.title = title
        self.hypothesis = hypothesis
        self.methodology = methodology
        self.novelty_score = novelty_score
        self.feasibility_score = feasibility_score
        self.required_methods = required_methods or []
        self.required_datasets = required_datasets or []
        self.metadata = metadata or {}
    
    @property
    def composite_score(self) -> float:
        """综合评分（新颖性 60% + 可行性 40%）"""
        return self.novelty_score * 0.6 + self.feasibility_score * 0.4
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "hypothesis": self.hypothesis,
            "methodology": self.methodology,
            "novelty_score": self.novelty_score,
            "feasibility_score": self.feasibility_score,
            "composite_score": self.composite_score,
            "required_methods": self.required_methods,
            "required_datasets": self.required_datasets,
            "metadata": self.metadata,
        }


# ============================================================
# 假设生成器
# ============================================================

class HypothesisGenerator:
    """基于知识图谱方法论生成研究假设"""
    
    def __init__(self, db=None):
        self._db = db
    
    def generate_hypotheses(
        self,
        concept_id: str,
        methodology: str = "all",
        max_per_method: int = 3,
    ) -> list[ResearchHypothesis]:
        """
        生成研究假设
        
        Args:
            concept_id: 概念 ID
            methodology: 方法论类型，"all" 表示使用所有方法
            max_per_method: 每种方法最多生成的假设数
        
        Returns:
            按综合评分排序的假设列表
        """
        if not self._db:
            raise ValueError("数据库未初始化")
        
        # 获取概念信息
        concept = self._db.get_concept_by_id(concept_id)
        if not concept:
            raise ValueError(f"未找到概念 ID: {concept_id}")
        
        # 获取图谱结构
        children = self._db.get_concept_children(concept_id) or []
        parents = self._db.get_concept_parents(concept_id) or []
        siblings = self._db.get_concept_siblings(concept_id) or []
        related_papers = self._db.get_papers_by_concept(concept_id) or []
        
        # 准备上下文
        context = {
            "concept_name": concept.get("text", ""),
            "concept_category": concept.get("category", ""),
            "parent_concepts": ", ".join([p.get("text", "") for p in parents[:5]]) or "无",
            "child_concepts": ", ".join([c.get("text", "") for c in children[:10]]) or "无",
            "sibling_concepts": ", ".join([s.get("text", "") for s in siblings[:10]]) or "无",
            "related_papers_info": self._format_papers_info(related_papers[:5]),
        }
        
        # 确定要使用的方法论
        if methodology == "all":
            methods = list(METHODOLOGY_CONFIGS.keys())
        else:
            methods = [methodology]
        
        # 对每种方法论生成假设
        all_hypotheses = []
        for method_key in methods:
            config = METHODOLOGY_CONFIGS[method_key]
            hypotheses = self._generate_with_method(
                method_key=method_key,
                config=config,
                context=context,
                max_count=max_per_method,
            )
            all_hypotheses.extend(hypotheses)
        
        # 按综合评分排序
        all_hypotheses.sort(key=lambda h: h.composite_score, reverse=True)
        
        return all_hypotheses
    
    def _format_papers_info(self, papers: list[dict]) -> str:
        """格式化论文信息"""
        if not papers:
            return "暂无相关论文"
        lines = []
        for i, p in enumerate(papers, 1):
            title = p.get("title", "未知标题")
            year = p.get("year", "")
            lines.append(f"{i}. {title} ({year})")
        return "\n".join(lines)
    
    def _generate_with_method(
        self,
        method_key: str,
        config: dict,
        context: dict,
        max_count: int,
    ) -> list[ResearchHypothesis]:
        """使用指定方法论生成假设"""
        llm = get_llm_or_raise()
        
        # 构建 prompt
        prompt = config["prompt_template"].format(**context)
        
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            content = response.content if hasattr(response, "content") else str(response)
            
            # 解析 JSON
            hypotheses = self._parse_json_response(content, method_key)
            
            # 限制数量
            return hypotheses[:max_count]
            
        except Exception as e:
            # 返回空列表，不影响其他方法论
            print(f"[HypothesisGenerator] {config['name']} 方法生成失败: {e}")
            return []
    
    def _parse_json_response(
        self,
        content: str,
        method_key: str,
    ) -> list[ResearchHypothesis]:
        """解析 LLM 的 JSON 响应"""
        # 提取 JSON 数组
        json_match = re.search(r'\[[\s\S]*\]', content)
        if not json_match:
            return []
        
        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            return []
        
        if not isinstance(data, list):
            return []
        
        hypotheses = []
        config = METHODOLOGY_CONFIGS[method_key]
        
        for item in data:
            if not isinstance(item, dict):
                continue
            
            hypothesis = ResearchHypothesis(
                title=item.get("title", ""),
                hypothesis=item.get("hypothesis", ""),
                methodology=config["name"],
                novelty_score=float(item.get("novelty_score", 0.5)),
                feasibility_score=float(item.get("feasibility_score", 0.5)),
                required_methods=item.get("required_methods", []),
                required_datasets=item.get("required_datasets", []),
                metadata={
                    k: v for k, v in item.items()
                    if k not in ("title", "hypothesis", "novelty_score", "feasibility_score",
                                "required_methods", "required_datasets")
                },
            )
            
            if hypothesis.title and hypothesis.hypothesis:
                hypotheses.append(hypothesis)
        
        return hypotheses


# ============================================================
# 多 Agent 假设评审
# ============================================================

REVIEW_PROMPT = """你是学术研究评审专家。请评审以下研究假设，给出修正建议。

## 方法论背景
{methodology_description}

## 待评审的假设
{hypothesis_text}

## 评审要求
1. 假设是否清晰、具体、可测试？
2. 新颖性评分是否合理？
3. 可行性评分是否合理？
4. 有什么具体的改进建议？

以 JSON 格式返回：
{
    "review": "总体评价",
    "novelty_adjustment": 0.0,  // 新颖性调整值 (-0.2 到 +0.2)
    "feasibility_adjustment": 0.0,  // 可行性调整值
    "suggestions": ["改进建议1", "改进建议2"]
}"""


async def review_hypothesis(
    hypothesis: ResearchHypothesis,
    concept_context: dict,
) -> ResearchHypothesis:
    """
    多 Agent 评审假设
    
    Args:
        hypothesis: 待评审的假设
        concept_context: 概念上下文
    
    Returns:
        评审后调整过的假设
    """
    llm = get_llm_or_raise()
    
    config = METHODOLOGY_CONFIGS.get(hypothesis.methodology.lower().replace(" ", "_"), {})
    methodology_desc = config.get("description", hypothesis.methodology)
    
    hypothesis_text = f"""
标题: {hypothesis.title}
假设: {hypothesis.hypothesis}
新颖性: {hypothesis.novelty_score}
可行性: {hypothesis.feasibility_score}
方法论: {hypothesis.methodology}
"""
    
    prompt = REVIEW_PROMPT.format(
        methodology_description=methodology_desc,
        hypothesis_text=hypothesis_text,
    )
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content if hasattr(response, "content") else str(response)
        
        # 解析评审结果
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            review = json.loads(json_match.group())
            
            # 应用调整
            hypothesis.novelty_score = max(0, min(1,
                hypothesis.novelty_score + review.get("novelty_adjustment", 0)
            ))
            hypothesis.feasibility_score = max(0, min(1,
                hypothesis.feasibility_score + review.get("feasibility_adjustment", 0)
            ))
            hypothesis.metadata["review"] = review
        
    except Exception as e:
        print(f"[HypothesisReview] 评审失败: {e}")
    
    return hypothesis
