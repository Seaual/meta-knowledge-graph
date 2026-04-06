# mkg/agent/state.py
"""
LangGraph Agent 状态定义
"""

from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """
    LangGraph Agent 统一状态

    所有节点共享此状态，通过 Annotated 实现消息自动累加
    """

    # 对话历史（自动累加）
    messages: Annotated[List[BaseMessage], add_messages]

    # 上下文（当前关注的目标）
    current_target: Optional[Dict[str, Any]]  # {type: "paper"|"concept", id: str, name: str}
    uploaded_papers: List[Dict[str, str]]     # [{doi: str, title: str}]

    # 路由决策
    intent: str      # lead | citation | research | deep_research | paper_qa | move_paper
    target_name: Optional[str]

    # 输出
    response: str
    agent_used: str
    needs_summary: bool  # 是否需要 Lead Agent 汇总
    concept_data: Optional[Dict[str, Any]]  # deprecated，向后兼容
    attachments: Optional[List[Dict[str, Any]]]  # 新增：[{type: str, data: dict}]