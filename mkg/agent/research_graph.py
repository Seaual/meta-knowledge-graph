# mkg/agent/research_graph.py
"""
Deep Research 多智能体架构

使用 LangGraph 实现多维度并行研究
"""

import json
import asyncio
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage

from mkg.llm import get_llm_or_raise, generate


class ResearchState(TypedDict):
    """研究状态"""
    target_name: str
    target_type: str
    query: str
    dimensions: List[str]
    dimension_findings: Dict[str, str]
    final_report: str


def coordinator_node(state: ResearchState) -> Dict[str, Any]:
    """
    协调者节点 - 规划研究维度

    分析研究目标，生成 3-5 个研究维度
    """
    llm = get_llm_or_raise()

    prompt = f"""分析以下研究目标，规划 3-5 个研究维度。

目标：{state['target_name']} ({state['target_type']})
研究问题：{state['query']}

要求：
- 维度应该覆盖不同角度（如技术、应用、趋势、挑战等）
- 每个维度用一个简短的词组描述

返回 JSON 数组格式：["维度1", "维度2", "维度3", ...]
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()

        # 处理可能的 markdown 代码块
        if content.startswith('```'):
            lines = content.split('\n')
            start_idx = 1
            end_idx = len(lines)
            if lines[-1].strip() == '```':
                end_idx = len(lines) - 1
            content = '\n'.join(lines[start_idx:end_idx])

        dimensions = json.loads(content)

        if not isinstance(dimensions, list):
            dimensions = ["技术分析", "应用场景", "发展趋势"]

        return {"dimensions": dimensions[:5]}

    except Exception as e:
        # 默认维度
        return {"dimensions": ["技术分析", "应用场景", "发展趋势", "挑战与机遇"]}


async def dimension_agent_async(dimension: str, target_name: str, target_type: str, query: str) -> tuple:
    """
    单维度异步研究
    """
    llm = get_llm_or_raise()

    prompt = f"""从「{dimension}」维度进行深入研究。

研究目标：{target_name} ({target_type})
核心问题：{query}

要求：
- 基于该维度提供深入的分析
- 包含具体的事实或数据支撑
- 给出有价值的见解

输出该维度的研究发现（200字以内）。
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return (dimension, response.content)
    except Exception as e:
        return (dimension, f"分析失败: {str(e)}")


def research_node(state: ResearchState) -> Dict[str, Any]:
    """
    研究节点 - 并行执行各维度研究
    """
    async def run_all_dimensions():
        tasks = [
            dimension_agent_async(
                dimension=dim,
                target_name=state['target_name'],
                target_type=state['target_type'],
                query=state['query']
            )
            for dim in state['dimensions']
        ]
        results = await asyncio.gather(*tasks)
        return dict(results)

    # 运行异步任务
    findings = asyncio.run(run_all_dimensions())

    return {"dimension_findings": findings}


def synthesizer_node(state: ResearchState) -> Dict[str, Any]:
    """
    综合者节点 - 汇总各维度发现，生成报告
    """
    llm = get_llm_or_raise()

    # 格式化各维度发现
    findings_text = "\n\n".join([
        f"### {dim}\n{finding}"
        for dim, finding in state['dimension_findings'].items()
    ])

    prompt = f"""综合以下各维度的研究发现，生成完整的研究报告。

## 研究目标
{state['target_name']} ({state['target_type']})
核心问题：{state['query']}

## 各维度发现
{findings_text}

## 要求
生成结构化报告，包含：
1. **摘要**（50字以内概括主要发现）
2. **各维度分析**（整合上述发现，避免重复）
3. **结论与建议**（基于分析给出可操作的建议）

使用 Markdown 格式输出。
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return {"final_report": response.content}
    except Exception as e:
        return {"final_report": f"报告生成失败: {str(e)}"}


def build_research_graph():
    """
    构建研究多智能体图
    """
    graph = StateGraph(ResearchState)

    # 添加节点
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("research", research_node)
    graph.add_node("synthesizer", synthesizer_node)

    # 设置流程
    graph.set_entry_point("coordinator")
    graph.add_edge("coordinator", "research")
    graph.add_edge("research", "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph.compile()


def run_deep_research(
    target_name: str,
    target_type: str,
    query: str,
    dimensions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    执行深入研究

    Args:
        target_name: 研究目标名称
        target_type: 目标类型 ('concept' | 'paper')
        query: 研究问题
        dimensions: 预设维度（可选）

    Returns:
        研究报告和中间结果
    """
    graph = build_research_graph()

    initial_state: ResearchState = {
        "target_name": target_name,
        "target_type": target_type,
        "query": query,
        "dimensions": dimensions or [],
        "dimension_findings": {},
        "final_report": "",
    }

    result = graph.invoke(initial_state)

    return {
        "report": result["final_report"],
        "dimensions": result["dimensions"],
        "findings": result["dimension_findings"],
    }