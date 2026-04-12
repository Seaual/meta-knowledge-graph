# mkg/agent/evolution_graph.py
"""
自演化研究编排器 - Phase 1

从"研究点发现"到"论文生成"的完整流水线：
1. 理解概念 - 从知识图谱获取概念上下文
2. 生成假设 - 基于 4 种方法论生成研究假设
3. 评审假设 - 多 Agent 评审假设
4. 文献调研 - 基于假设搜索文献
5. 实验设计 - 设计实验方案
6. 撰写论文 - 分段生成 IMRAD 结构论文
7. 论文评审 - 多 Agent 评审论文
"""

import asyncio
import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from mkg.llm import get_llm_or_raise
from mkg.agent.nodes.hypothesis_node import (
    HypothesisGenerator,
    ResearchHypothesis,
    review_hypothesis,
)

# ============================================================
# 全局进度存储
# ============================================================

_evolution_progress: dict[str, dict[str, Any]] = {}


def get_evolution_progress(run_id: str) -> dict[str, Any] | None:
    """获取演化研究进度"""
    return _evolution_progress.get(run_id)


# ============================================================
# 演化状态
# ============================================================


@dataclass
class EvolutionState:
    """演化研究状态"""

    run_id: str
    concept_id: str
    mode: str = "auto"  # auto | co-pilot

    # Stage 1
    concept_context: dict = field(default_factory=dict)

    # Stage 2
    hypotheses: list[ResearchHypothesis] = field(default_factory=list)

    # Stage 3
    selected_hypothesis: dict | None = None

    # Stage 4
    literature_review: str = ""
    key_references: list[dict] = field(default_factory=list)

    # Stage 5
    experiment_plan: dict = field(default_factory=dict)
    baselines: list[str] = field(default_factory=list)
    datasets: list[str] = field(default_factory=list)

    # Stage 6
    paper_sections: dict = field(default_factory=dict)

    # Stage 7
    review_report: dict = field(default_factory=dict)
    final_paper: str = ""


# ============================================================
# 阶段 1: 理解概念
# ============================================================


def stage_understand_concept(state: EvolutionState, db) -> EvolutionState:
    """从知识图谱获取概念上下文"""
    concept = db.get_concept(state.concept_id)
    if not concept:
        raise ValueError(f"概念不存在: {state.concept_id}")

    parents = db.get_concept_parents(state.concept_id)
    children = db.get_concept_children(state.concept_id)

    # 获取相关论文（概念提取记录）
    paper_dois = set()
    for c in [concept] + children:
        papers = db.get_concepts_by_paper(c.get("id", ""))
        for p in papers:
            paper_dois.add(p.get("paper_doi", ""))

    related_papers = []
    for doi in list(paper_dois)[:10]:
        paper = db.get_paper(doi)
        if paper:
            related_papers.append(paper)

    state.concept_context = {
        "concept": concept,
        "parents": parents,
        "children": children,
        "related_papers": related_papers,
    }

    _update_progress(state.run_id, stage=1, stage_name="理解概念", progress=15)
    return state


# ============================================================
# 阶段 2: 生成假设
# ============================================================


def stage_generate_hypotheses(state: EvolutionState, db) -> EvolutionState:
    """生成研究假设"""
    generator = HypothesisGenerator(db=db)
    hypotheses = generator.generate_hypotheses(
        concept_id=state.concept_id,
        max_per_method=3,
    )
    state.hypotheses = hypotheses

    _update_progress(
        state.run_id,
        stage=2,
        stage_name="生成假设",
        progress=30,
        details={"hypothesis_count": len(hypotheses)},
    )
    return state


# ============================================================
# 阶段 3: 评审假设
# ============================================================


def stage_review_hypotheses(state: EvolutionState, db) -> EvolutionState:
    """多 Agent 评审假设，选择最优假设"""
    if not state.hypotheses:
        _update_progress(state.run_id, stage=3, stage_name="评审假设", progress=40)
        return state

    # 评审前 3 个评分最高的假设
    top_hypotheses = state.hypotheses[:3]
    reviews = []

    for h in top_hypotheses:
        h_dict = {
            "title": h.title,
            "hypothesis": h.hypothesis,
            "methodology": h.methodology,
            "novelty_score": h.novelty_score,
            "feasibility_score": h.feasibility_score,
        }
        review = review_hypothesis(h_dict, state.concept_context)
        reviews.append(review)

    # 选择综合评分最高的假设
    if reviews:
        best_idx = max(
            range(len(reviews)),
            key=lambda i: reviews[i].get("overall_score", 0),
        )
        best_h = top_hypotheses[best_idx]
        state.selected_hypothesis = {
            "title": best_h.title,
            "hypothesis": best_h.hypothesis,
            "methodology": best_h.methodology,
            "novelty_score": best_h.novelty_score,
            "feasibility_score": best_h.feasibility_score,
            "required_methods": best_h.required_methods,
            "required_datasets": best_h.required_datasets,
            "description": best_h.description,
            "review": reviews[best_idx],
        }

    _update_progress(
        state.run_id,
        stage=3,
        stage_name="评审假设",
        progress=45,
        details={"selected": state.selected_hypothesis.get("title") if state.selected_hypothesis else None},
    )
    return state


# ============================================================
# 阶段 4: 文献调研
# ============================================================


async def stage_literature_survey(state: EvolutionState, db) -> EvolutionState:
    """基于假设搜索文献"""
    if not state.selected_hypothesis:
        _update_progress(state.run_id, stage=4, stage_name="文献调研", progress=50)
        return state

    hypothesis = state.selected_hypothesis

    # 生成搜索查询
    llm = get_llm_or_raise()
    query_prompt = f"""基于以下研究假设，生成 3-5 个用于搜索相关文献的关键词或短语。

假设: {hypothesis['hypothesis']}
所需方法: {', '.join(hypothesis.get('required_methods', []))}

只返回 JSON 数组格式，不要其他内容: ["关键词1", "关键词2", ...]"""

    try:
        response = llm.invoke([HumanMessage(content=query_prompt)])
        content = _extract_text(response.content)
        text = _clean_json(content)
        search_terms = json.loads(text)
    except Exception:
        search_terms = [hypothesis["title"]]

    # 搜索文献 - 从数据库已有的论文中搜索
    key_references = []
    seen_dois = set()

    for term in search_terms:
        if isinstance(term, str):
            papers = db.search_papers(term, limit=5)
            for p in papers:
                doi = p.get("doi", "")
                if doi and doi not in seen_dois:
                    seen_dois.add(doi)
                    key_references.append({
                        "doi": doi,
                        "title": p.get("title", ""),
                        "abstract": p.get("abstract", ""),
                    })

    # 生成文献综述
    if key_references:
        ref_titles = [r["title"] for r in key_references[:10]]
        lit_review_prompt = f"""基于以下研究假设和相关文献，生成一段文献综述。

研究假设: {hypothesis['title']}
假设内容: {hypothesis['hypothesis']}

相关文献 ({len(key_references)} 篇):
{_format_paper_list(key_references[:10])}

请撰写一段 300 字以内的文献综述，包括：
1. 该领域的研究现状
2. 现有研究的不足
3. 本假设可能做出的贡献

用 Markdown 格式输出。"""

        try:
            response = llm.invoke([HumanMessage(content=lit_review_prompt)])
            state.literature_review = _extract_text(response.content)
        except Exception:
            state.literature_review = "文献综述生成失败"
    else:
        state.literature_review = "未找到相关参考文献"

    state.key_references = key_references[:20]

    _update_progress(
        state.run_id,
        stage=4,
        stage_name="文献调研",
        progress=60,
        details={"reference_count": len(key_references)},
    )
    return state


# ============================================================
# 阶段 5: 实验设计
# ============================================================


async def stage_experiment_design(state: EvolutionState, db) -> EvolutionState:
    """设计实验方案"""
    if not state.selected_hypothesis:
        _update_progress(state.run_id, stage=5, stage_name="实验设计", progress=65)
        return state

    llm = get_llm_or_raise()
    hypothesis = state.selected_hypothesis

    prompt = f"""基于以下研究假设和文献综述，设计完整的实验方案。

研究假设: {hypothesis['title']}
假设内容: {hypothesis['hypothesis']}
所需方法: {', '.join(hypothesis.get('required_methods', []))}
所需数据集: {', '.join(hypothesis.get('required_datasets', []))}

文献综述:
{state.literature_review[:500]}

请返回 JSON 格式，包含以下字段：
- objective: 实验目标（100字以内）
- methodology: 实验方法描述（200字以内）
- datasets: 推荐使用的数据集列表
- baselines: 需要对比的基线方法列表（至少3个）
- metrics: 评估指标列表
- procedure: 实验步骤列表（每步一个字符串）
- expected_results: 预期结果描述

只返回 JSON，不要其他内容。"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = _extract_text(response.content)
        text = _clean_json(content)
        plan = json.loads(text)

        state.experiment_plan = plan
        state.baselines = plan.get("baselines", [])
        state.datasets = plan.get("datasets", [])
    except Exception as e:
        state.experiment_plan = {"error": str(e)}
        state.baselines = hypothesis.get("required_methods", [])[:3]
        state.datasets = hypothesis.get("required_datasets", [])[:3]

    _update_progress(
        state.run_id,
        stage=5,
        stage_name="实验设计",
        progress=75,
    )
    return state


# ============================================================
# 阶段 6: 撰写论文
# ============================================================


async def stage_write_paper(state: EvolutionState, db) -> EvolutionState:
    """分段撰写论文（IMRAD 结构）"""
    if not state.selected_hypothesis:
        _update_progress(state.run_id, stage=6, stage_name="撰写论文", progress=80)
        return state

    llm = get_llm_or_raise()
    hypothesis = state.selected_hypothesis

    sections = ["introduction", "related_work", "method", "experiment", "results", "discussion", "conclusion"]
    section_titles = {
        "introduction": "引言",
        "related_work": "相关工作",
        "method": "方法",
        "experiment": "实验设计",
        "results": "结果与分析",
        "discussion": "讨论",
        "conclusion": "结论",
    }

    context = _build_paper_context(state)

    for i, section in enumerate(sections):
        progress = 80 + int(15 * (i + 1) / len(sections))
        _update_progress(
            state.run_id,
            stage=6,
            stage_name="撰写论文",
            progress=progress,
            details={"writing_section": section_titles[section]},
        )

        section_prompt = _build_section_prompt(section, hypothesis, context)
        try:
            response = llm.invoke([HumanMessage(content=section_prompt)])
            state.paper_sections[section] = _extract_text(response.content)
        except Exception as e:
            state.paper_sections[section] = f"[{section_titles[section]} 生成失败: {str(e)}]"

    # 组装完整论文
    full_paper_parts = []
    for section in sections:
        title = section_titles.get(section, section)
        content = state.paper_sections.get(section, "")
        full_paper_parts.append(f"# {title}\n\n{content}")

    state.final_paper = "\n\n---\n\n".join(full_paper_parts)

    _update_progress(
        state.run_id,
        stage=6,
        stage_name="撰写论文",
        progress=95,
    )
    return state


# ============================================================
# 阶段 7: 论文评审
# ============================================================


async def stage_review_paper(state: EvolutionState, db) -> EvolutionState:
    """多 Agent 评审论文"""
    if not state.final_paper:
        _update_progress(state.run_id, stage=7, stage_name="论文评审", progress=100)
        return state

    llm = get_llm_or_raise()
    hypothesis = state.selected_hypothesis

    # 截取论文前 8000 字符（避免超出 token 限制）
    paper_excerpt = state.final_paper[:8000]

    prompt = f"""你是顶级会议的论文评审专家（Reviewer）。请从以下维度评审这篇研究论文：

1. 创新性（Originality）: 研究问题和方法是否有新意？
2. 技术质量（Technical Quality）: 方法论是否严谨？
3. 实验设计（Experimental Design）: 实验设置是否合理？基线是否充分？
4. 写作质量（Writing Quality）: 论文表达是否清晰？
5. 潜在影响力（Impact）: 对该领域的贡献有多大？

研究假设: {hypothesis.get('title', '')}
假设内容: {hypothesis.get('hypothesis', '')}

论文内容:
{paper_excerpt}

请返回 JSON 格式，包含以下字段：
- originality_score: 创新性评分（0-100）
- technical_quality_score: 技术质量评分（0-100）
- experimental_design_score: 实验设计评分（0-100）
- writing_quality_score: 写作质量评分（0-100）
- impact_score: 潜在影响力评分（0-100）
- overall_score: 综合评分（0-100）
- recommendation: 推荐结论（"accept" / "weak_accept" / "borderline" / "reject"）
- strengths: 优势列表（3-5条）
- weaknesses: 弱点列表（3-5条）
- suggestions_for_revision: 修改建议列表
- overall_comment: 总体评价（200字以内）

只返回 JSON，不要其他内容。"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = _extract_text(response.content)
        text = _clean_json(content)
        review = json.loads(text)
        state.review_report = review
    except Exception as e:
        state.review_report = {"error": str(e), "overall_comment": "评审失败"}

    _update_progress(
        state.run_id,
        stage=7,
        stage_name="论文评审",
        progress=100,
        details={"completed": True},
    )
    return state


# ============================================================
# 主编排函数
# ============================================================


async def run_evolution_research(
    db,
    concept_id: str,
    run_id: str | None = None,
    mode: str = "auto",
) -> dict[str, Any]:
    """
    运行完整的自演化研究流程

    Args:
        db: Database 实例
        concept_id: 概念 ID
        run_id: 运行 ID（自动生成）
        mode: 运行模式（auto | co-pilot）

    Returns:
        包含最终论文和中间结果的字典
    """
    run_id = run_id or str(uuid.uuid4())[:12]

    _evolution_progress[run_id] = {
        "run_id": run_id,
        "concept_id": concept_id,
        "mode": mode,
        "status": "running",
        "current_stage": 0,
        "progress": 0,
        "stages_completed": [],
    }

    state = EvolutionState(run_id=run_id, concept_id=concept_id, mode=mode)

    try:
        # Stage 1: 理解概念
        state = stage_understand_concept(state, db)

        # Stage 2: 生成假设
        state = stage_generate_hypotheses(state, db)

        # Stage 3: 评审假设
        state = stage_review_hypotheses(state, db)

        # Stage 4-7: 异步阶段
        state = await stage_literature_survey(state, db)
        state = await stage_experiment_design(state, db)
        state = await stage_write_paper(state, db)
        state = await stage_review_paper(state, db)

        # 标记完成
        _evolution_progress[run_id]["status"] = "completed"
        _evolution_progress[run_id]["progress"] = 100

        return {
            "run_id": run_id,
            "status": "completed",
            "concept_context": state.concept_context,
            "hypotheses_count": len(state.hypotheses),
            "selected_hypothesis": state.selected_hypothesis,
            "key_references_count": len(state.key_references),
            "experiment_plan": state.experiment_plan,
            "paper_sections": state.paper_sections,
            "final_paper": state.final_paper,
            "review_report": state.review_report,
        }

    except Exception as e:
        _evolution_progress[run_id]["status"] = "error"
        _evolution_progress[run_id]["error"] = str(e)

        return {
            "run_id": run_id,
            "status": "error",
            "error": str(e),
            "concept_context": state.concept_context,
            "hypotheses_count": len(state.hypotheses),
            "selected_hypothesis": state.selected_hypothesis,
            "final_paper": state.final_paper or "",
        }


def run_evolution_research_sync(
    db,
    concept_id: str,
    run_id: str | None = None,
    mode: str = "auto",
) -> dict[str, Any]:
    """同步版本的自演化研究（用于 API 调用）"""
    return asyncio.run(run_evolution_research(db, concept_id, run_id, mode))


# ============================================================
# 辅助函数
# ============================================================


def _update_progress(run_id: str, stage: int, stage_name: str, progress: int, details: dict | None = None):
    """更新研究进度"""
    if run_id not in _evolution_progress:
        return

    entry = _evolution_progress[run_id]
    entry["current_stage"] = stage
    entry["stage_name"] = stage_name
    entry["progress"] = progress
    entry["updated_at"] = _now_iso()

    if details:
        entry["details"] = details


def _build_paper_context(state: EvolutionState) -> dict:
    """构建论文写作的上下文"""
    return {
        "hypothesis": state.selected_hypothesis,
        "literature_review": state.literature_review,
        "key_references": state.key_references[:10],
        "experiment_plan": state.experiment_plan,
        "baselines": state.baselines,
        "datasets": state.datasets,
    }


def _build_section_prompt(section: str, hypothesis: dict, context: dict) -> str:
    """为每个 IMRAD 部分构建 prompt"""
    section_instructions: dict[str, str] = {
        "introduction": """撰写论文的引言部分。包括：
- 研究背景和问题的重要性
- 现有研究的不足
- 本文的贡献和创新点
- 论文结构概述
要求 500-800 字。""",

        "related_work": """撰写相关工作部分。包括：
- 与本研究最相关的工作综述
- 现有方法的局限性
- 本文与现有工作的区别
要求 500-800 字。""",

        "method": """撰写方法部分。包括：
- 提出的方法/框架详细描述
- 理论分析和算法描述
- 方法的优势和创新点
要求 800-1200 字。""",

        "experiment": """撰写实验设计部分。包括：
- 数据集描述
- 评估指标
- 基线方法
- 实验设置和参数
要求 400-600 字。""",

        "results": """撰写结果与分析部分。包括：
- 主要实验结果（使用表格描述）
- 与基线方法的对比
- 消融实验结果
- 统计分析
要求 500-800 字。""",

        "discussion": """撰写讨论部分。包括：
- 结果的解释和意义
- 方法的局限性
- 对未来工作的展望
要求 300-500 字。""",

        "conclusion": """撰写结论部分。包括：
- 研究的主要发现
- 理论贡献和实际意义
- 局限性和未来方向
要求 200-300 字。""",
    }

    refs_info = ""
    if context.get("key_references"):
        ref_lines = [
            f"{i+1}. {r.get('title', '')}"
            for i, r in enumerate(context["key_references"][:5])
        ]
        refs_info = "\n关键参考文献:\n" + "\n".join(ref_lines)

    prompt = f"""你是一位学术论文写作专家。请撰写论文的「{section}」部分。

研究假设:
标题: {hypothesis.get('title', '')}
内容: {hypothesis.get('hypothesis', '')}
方法论: {hypothesis.get('methodology', '')}
{refs_info}

实验方案:
{json.dumps(context.get('experiment_plan', {}), ensure_ascii=False, indent=2)}

基线方法: {', '.join(context.get('baselines', []))}
数据集: {', '.join(context.get('datasets', []))}

要求：
{section_instructions.get(section, '')}

注意：
- 使用学术论文的正式写作风格
- 使用 Markdown 格式
- 不要编造具体的数值结果，用「如表X所示」这样的引用方式
- 确保与其他部分的内容一致
- 只输出该部分的内容，不要包含其他部分"""

    return prompt


def _format_paper_list(papers: list[dict]) -> str:
    """格式化论文列表为文本"""
    lines = []
    for i, p in enumerate(papers, 1):
        title = p.get("title", "Unknown")
        abstract = p.get("abstract", "")[:200]
        lines.append(f"{i}. {title}")
        if abstract:
            lines.append(f"   摘要: {abstract}")
    return "\n".join(lines)


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


def _clean_json(text: str) -> str:
    """清理 JSON 字符串（移除 markdown 代码块）"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        start = 1
        # 跳过 ```json 或 ``` 开头的行
        if start < len(lines) and lines[0].strip().startswith("```json"):
            start = 1
        elif start < len(lines) and lines[0].strip() == "```":
            start = 1
        end = len(lines) if not lines[-1].strip().startswith("```") else len(lines) - 1
        text = "\n".join(lines[start:end]).strip()
    return text


def _now_iso() -> str:
    """当前时间 ISO 格式"""
    import datetime
    return datetime.datetime.now().isoformat()
