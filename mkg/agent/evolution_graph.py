# mkg/agent/evolution_graph.py
"""
MKG 自演化研究编排器

从知识图谱发现研究假设 → 文献调研 → 实验设计 → 论文撰写 → 评审验证

核心差异化：不是用户给 idea 写论文，而是让图谱告诉你该研究什么，然后自动写出来。
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Any

from langchain_core.messages import HumanMessage

from mkg.llm import get_llm_or_raise

from .nodes.hypothesis_node import (
    HypothesisGenerator,
    ResearchHypothesis,
    METHODOLOGY_CONFIGS,
    review_hypothesis,
)


# ============================================================
# 进度存储
# ============================================================

_evolution_progress: dict[str, dict[str, Any]] = {}


def get_evolution_progress(run_id: str) -> dict[str, Any] | None:
    """获取研究运行进度"""
    return _evolution_progress.get(run_id)


def _update_progress(run_id: str, stage: str, progress: int, data: dict | None = None):
    """更新研究进度"""
    if run_id not in _evolution_progress:
        _evolution_progress[run_id] = {
            "status": "running",
            "current_stage": "",
            "progress": 0,
            "stages_completed": [],
            "data": {},
        }
    _evolution_progress[run_id].update({
        "current_stage": stage,
        "progress": progress,
        "data": {**_evolution_progress[run_id].get("data", {}), **(data or {})},
    })


def _complete_progress(run_id: str):
    """标记研究完成"""
    if run_id in _evolution_progress:
        _evolution_progress[run_id].update({
            "status": "completed",
            "progress": 100,
        })


# ============================================================
# 研究运行状态
# ============================================================

@dataclass
class EvolutionState:
    """自演化研究状态"""
    run_id: str
    concept_id: str
    mode: str = "auto"  # auto | co-pilot
    
    # Stage 1: 概念理解
    concept_context: dict = field(default_factory=dict)
    research_points: list = field(default_factory=list)
    
    # Stage 2: 假设生成
    hypotheses: list[ResearchHypothesis] = field(default_factory=list)
    selected_hypothesis: dict | None = None
    
    # Stage 3: 文献调研
    literature_review: str = ""
    key_references: list[dict] = field(default_factory=list)
    
    # Stage 4: 实验设计
    experiment_plan: dict = field(default_factory=dict)
    baselines: list[str] = field(default_factory=list)
    datasets: list[str] = field(default_factory=list)
    
    # Stage 5: 论文撰写
    paper_sections: dict = field(default_factory=dict)
    
    # Stage 6: 评审验证
    review_report: dict = field(default_factory=dict)
    final_paper: str = ""


# ============================================================
# 阶段节点实现
# ============================================================

def stage_understand_concept(state: EvolutionState, db) -> EvolutionState:
    """
    Stage 1: 概念理解
    
    从知识图谱获取概念的完整上下文：层次结构、相关论文、现有研究点
    """
    _update_progress(state.run_id, "概念理解", 10)
    
    concept = db.get_concept_by_id(state.concept_id)
    if not concept:
        raise ValueError(f"概念不存在: {state.concept_id}")
    
    # 获取图谱结构
    children = db.get_concept_children(state.concept_id) or []
    parents = db.get_concept_parents(state.concept_id) or []
    siblings = db.get_concept_siblings(state.concept_id) or []
    related_papers = db.get_papers_by_concept(state.concept_id) or []
    
    # 获取现有研究点
    try:
        from mkg.agent.tools import analyze_research_points
        research_result = analyze_research_points.invoke({"concept_name": concept.get("text", "")})
        research_points = research_result.get("research_points", [])
    except Exception:
        research_points = []
    
    state.concept_context = {
        "concept": concept,
        "parents": parents[:5],
        "children": children[:15],
        "siblings": siblings[:15],
        "related_papers": related_papers[:10],
    }
    state.research_points = research_points
    
    _update_progress(state.run_id, "概念理解", 20, {
        "concept_name": concept.get("text", ""),
        "paper_count": len(related_papers),
    })
    
    return state


def stage_generate_hypotheses(state: EvolutionState, db) -> EvolutionState:
    """
    Stage 2: 假设生成（核心）
    
    使用 4 种方法论生成研究假设，然后多 Agent 评审排序
    """
    _update_progress(state.run_id, "假设生成", 30)
    
    generator = HypothesisGenerator(db=db)
    hypotheses = generator.generate_hypotheses(
        concept_id=state.concept_id,
        methodology="all",
        max_per_method=3,
    )
    
    state.hypotheses = hypotheses
    
    _update_progress(state.run_id, "假设生成", 45, {
        "hypotheses_count": len(hypotheses),
        "hypotheses_preview": [h.to_dict() for h in hypotheses[:3]],
    })
    
    return state


async def stage_review_hypotheses_async(state: EvolutionState) -> EvolutionState:
    """
    Stage 2.5: 假设评审（异步）
    
    对生成的假设进行多 Agent 评审
    """
    if not state.hypotheses:
        return state
    
    # 评审 Top 3 假设
    reviewed = []
    for hyp in state.hypotheses[:3]:
        reviewed_hyp = await review_hypothesis(hyp, state.concept_context)
        reviewed.append(reviewed_hyp)
    
    # 重新排序
    reviewed.sort(key=lambda h: h.composite_score, reverse=True)
    state.hypotheses = reviewed
    
    # 选择最佳假设
    if reviewed:
        state.selected_hypothesis = reviewed[0].to_dict()
    
    _update_progress(state.run_id, "假设评审", 55, {
        "reviewed_count": len(reviewed),
        "best_hypothesis": state.selected_hypothesis,
    })
    
    return state


def stage_literature_survey(state: EvolutionState, db) -> EvolutionState:
    """
    Stage 3: 文献调研
    
    基于选定的假设搜索相关文献，生成文献综述
    """
    _update_progress(state.run_id, "文献调研", 60)
    
    if not state.selected_hypothesis:
        return state
    
    hypothesis = state.selected_hypothesis
    
    # 搜索相关论文
    papers = db.get_papers_by_status("processed")[:20]
    
    # 构建文献综述 prompt
    llm = get_llm_or_raise()
    
    papers_info = "\n".join([
        f"- {p.get('title', '')} ({p.get('year', '')})"
        for p in papers[:10]
    ])
    
    prompt = f"""基于以下研究假设和相关论文，生成一段文献综述。

## 研究假设
{hypothesis['title']}
{hypothesis['hypothesis']}

## 相关论文
{papers_info if papers_info else '暂无相关论文'}

## 要求
1. 概述该研究方向的现状
2. 指出已有工作的不足
3. 说明本假设的创新点
4. 200-300 字
"""
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        state.literature_review = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        state.literature_review = f"文献综述生成失败: {e}"
    
    state.key_references = papers[:10]
    
    _update_progress(state.run_id, "文献调研", 65, {
        "references_count": len(state.key_references),
        "literature_review_preview": state.literature_review[:200],
    })
    
    return state


def stage_experiment_design(state: EvolutionState, db) -> EvolutionState:
    """
    Stage 4: 实验设计
    
    基于假设和文献综述设计实验方案
    """
    _update_progress(state.run_id, "实验设计", 70)
    
    if not state.selected_hypothesis:
        return state
    
    llm = get_llm_or_raise()
    hypothesis = state.selected_hypothesis
    
    prompt = f"""为以下研究假设设计实验方案。

## 研究假设
标题: {hypothesis['title']}
描述: {hypothesis['hypothesis']}
方法论: {hypothesis['methodology']}
需要的方法: {', '.join(hypothesis.get('required_methods', []))}
需要的数据集: {', '.join(hypothesis.get('required_datasets', []))}

## 文献综述
{state.literature_review[:500]}

## 任务
设计实验方案，包含：
1. 基线方法选择（2-3个）
2. 数据集选择
3. 评估指标
4. 实验步骤（3-5步）
5. 预期结果

以 JSON 格式返回：
{
    "baselines": ["基线方法1", "基线方法2"],
    "datasets": ["数据集1"],
    "metrics": ["指标1"],
    "steps": ["步骤1"],
    "expected_results": "预期结果描述"
}
"""
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content if hasattr(response, "content") else str(response)
        
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            plan = json.loads(json_match.group())
            state.experiment_plan = plan
            state.baselines = plan.get("baselines", [])
            state.datasets = plan.get("datasets", [])
    except Exception as e:
        state.experiment_plan = {"error": str(e)}
    
    _update_progress(state.run_id, "实验设计", 75, {
        "baselines": state.baselines,
        "datasets": state.datasets,
    })
    
    return state


def stage_write_paper(state: EvolutionState, db) -> EvolutionState:
    """
    Stage 5: 论文撰写
    
    分段生成学术论文（IMRAD 结构）
    """
    _update_progress(state.run_id, "论文撰写", 80)
    
    if not state.selected_hypothesis:
        return state
    
    llm = get_llm_or_raise()
    hypothesis = state.selected_hypothesis
    
    sections = {
        "title": f"基于{hypothesis['methodology']}方法的研究：{hypothesis['title']}",
    }
    
    # 分段生成
    section_prompts = {
        "abstract": f"为以下研究生成 200 字摘要。\n假设: {hypothesis['title']}\n描述: {hypothesis['hypothesis']}",
        "introduction": f"撰写 Introduction，包含研究背景、动机、贡献列表。\n假设: {hypothesis['title']}\n文献综述: {state.literature_review[:300]}",
        "related_work": f"撰写 Related Work，基于以下文献综述。\n{state.literature_review}",
        "method": f"撰写 Method 章节，详细描述方法。\n实验方案: {json.dumps(state.experiment_plan, ensure_ascii=False)[:1000]}",
        "experiment": f"撰写 Experiment 章节，描述实验设计。\n基线: {state.baselines}\n数据集: {state.datasets}",
        "conclusion": f"撰写 Conclusion，总结研究贡献和未来工作。\n假设: {hypothesis['title']}",
    }
    
    for section_name, prompt in section_prompts.items():
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            sections[section_name] = response.content if hasattr(response, "content") else str(response)
            state.paper_sections[section_name] = sections[section_name]
        except Exception as e:
            sections[section_name] = f"[生成失败: {e}]"
    
    # 组装完整论文
    state.final_paper = assemble_paper(sections)
    
    _update_progress(state.run_id, "论文撰写", 90, {
        "sections_completed": list(sections.keys()),
    })
    
    return state


def stage_review_paper(state: EvolutionState, db) -> EvolutionState:
    """
    Stage 6: 评审验证
    
    多 Agent 评审论文
    """
    _update_progress(state.run_id, "评审验证", 95)
    
    if not state.final_paper:
        return state
    
    llm = get_llm_or_raise()
    
    prompt = f"""你是学术评审专家。请评审以下论文草稿。

{state.final_paper[:3000]}

## 评审要求
从以下维度给出评价和改进建议：
1. 创新性（0-10）
2. 方法论合理性（0-10）
3. 实验设计（0-10）
4. 写作质量（0-10）
5. 主要改进建议（3条）

以 JSON 格式返回。"""
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content if hasattr(response, "content") else str(response)
        
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            state.review_report = json.loads(json_match.group())
    except Exception as e:
        state.review_report = {"error": str(e)}
    
    _complete_progress(state.run_id)
    _update_progress(state.run_id, "完成", 100, {
        "review": state.review_report,
    })
    
    return state


def assemble_paper(sections: dict) -> str:
    """组装完整论文"""
    parts = []
    
    if "title" in sections:
        parts.append(f"# {sections['title']}\n")
    if "abstract" in sections:
        parts.append(f"## Abstract\n\n{sections['abstract']}\n")
    if "introduction" in sections:
        parts.append(f"## 1. Introduction\n\n{sections['introduction']}\n")
    if "related_work" in sections:
        parts.append(f"## 2. Related Work\n\n{sections['related_work']}\n")
    if "method" in sections:
        parts.append(f"## 3. Method\n\n{sections['method']}\n")
    if "experiment" in sections:
        parts.append(f"## 4. Experiment\n\n{sections['experiment']}\n")
    if "conclusion" in sections:
        parts.append(f"## 5. Conclusion\n\n{sections['conclusion']}\n")
    
    return "\n".join(parts)


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
    执行自演化研究
    
    Args:
        db: Database 实例
        concept_id: 概念 ID
        run_id: 运行 ID（可选，用于追踪）
        mode: 运行模式 (auto | co-pilot)
    
    Returns:
        研究结果字典
    """
    import uuid
    
    run_id = run_id or str(uuid.uuid4())[:8]
    state = EvolutionState(run_id=run_id, concept_id=concept_id, mode=mode)
    
    _evolution_progress[run_id] = {
        "status": "running",
        "current_stage": "",
        "progress": 0,
        "stages_completed": [],
        "data": {},
    }
    
    stages = [
        ("概念理解", lambda: stage_understand_concept(state, db)),
        ("假设生成", lambda: stage_generate_hypotheses(state, db)),
        ("假设评审", lambda: asyncio.run(stage_review_hypotheses_async(state))),
        ("文献调研", lambda: stage_literature_survey(state, db)),
        ("实验设计", lambda: stage_experiment_design(state, db)),
        ("论文撰写", lambda: stage_write_paper(state, db)),
        ("评审验证", lambda: stage_review_paper(state, db)),
    ]
    
    for stage_name, stage_func in stages:
        try:
            stage_func()
            _evolution_progress[run_id]["stages_completed"].append(stage_name)
        except Exception as e:
            _evolution_progress[run_id]["status"] = "error"
            _evolution_progress[run_id]["error"] = {
                "stage": stage_name,
                "message": str(e),
            }
            break
    
    return {
        "run_id": run_id,
        "status": _evolution_progress[run_id]["status"],
        "concept_id": state.concept_id,
        "selected_hypothesis": state.selected_hypothesis,
        "hypotheses": [h.to_dict() for h in state.hypotheses[:5]],
        "literature_review": state.literature_review,
        "experiment_plan": state.experiment_plan,
        "paper": state.final_paper,
        "review": state.review_report,
    }


def start_evolution_research_sync(
    db,
    concept_id: str,
    run_id: str | None = None,
    mode: str = "auto",
) -> str:
    """
    同步启动研究（用于 API 调用）
    
    Returns:
        run_id
    """
    import asyncio
    
    async def run():
        return await run_evolution_research(db, concept_id, run_id, mode)
    
    # 在后台运行
    result = asyncio.run(run())
    return result["run_id"]
