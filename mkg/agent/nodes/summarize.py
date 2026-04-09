# mkg/agent/nodes/summarize.py
"""
Summarize Node - 汇总节点
"""

from langchain_core.messages import HumanMessage, AIMessage
from typing import Dict, Any

from ..state import AgentState
from mkg.llm import get_llm_or_raise


SUMMARIZE_PROMPT = """以下是专业 Agent 生成的分析报告，请用简洁友好的方式总结要点：

{report}

请用中文总结（100字以内），突出关键发现。
- 用一两句话概括核心发现
- 提及最重要的数据或结论
- 语气友好，像一个助手在汇报"""


def summarize_node(state: AgentState) -> Dict[str, Any]:
    """
    Summarize Node - 汇总专业 Agent 的输出

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    llm = get_llm_or_raise()

    report = state.get("response", "")
    agent_used = state.get("agent_used", "unknown")

    prompt = SUMMARIZE_PROMPT.format(report=report)

    # 调用 LLM 汇总
    response = llm.invoke([HumanMessage(content=prompt)])

    summary = response.content

    return {
        "response": summary,
        "agent_used": agent_used,  # 保持原 agent 标记
        "needs_summary": False,
        "messages": [AIMessage(content=summary)],
    }