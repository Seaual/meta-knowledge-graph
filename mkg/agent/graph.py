# mkg/agent/graph.py
"""
LangGraph Agent 图定义 - 简化版

所有功能通过 lead node 的 tool 调用实现
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from mkg.llm import init_llm_from_db

from .nodes import lead_node
from .state import AgentState
from .tools import init_tools


def build_agent_graph(db=None, s2_client=None, pdf_parser=None):
    """
    构建 LangGraph Agent 图

    简化架构：只有一个 lead node，通过 tool 调用实现所有功能
    """
    # 初始化 LLM
    init_llm_from_db(db)

    # 初始化 Tools 依赖
    init_tools(db=db, s2_client=s2_client, pdf_parser=pdf_parser)

    # 创建图
    graph = StateGraph(AgentState)

    # 只添加一个节点
    graph.add_node("lead", lead_node)

    # 设置入口
    graph.set_entry_point("lead")

    # lead 直接结束
    graph.add_edge("lead", END)

    # 添加记忆持久化
    memory = MemorySaver()

    return graph.compile(checkpointer=memory)


# 单例
_compiled_graph = None


def get_agent_graph(db=None, s2_client=None, pdf_parser=None):
    """获取编译后的 Agent 图（单例）"""
    global _compiled_graph

    # 每次都初始化工具依赖（确保数据库等依赖正确设置）
    init_tools(db=db, s2_client=s2_client, pdf_parser=pdf_parser)

    # 初始化 LLM
    init_llm_from_db(db)

    if _compiled_graph is None:
        _compiled_graph = build_agent_graph(db, s2_client, pdf_parser)

    return _compiled_graph


def reset_graph():
    """重置图"""
    global _compiled_graph
    _compiled_graph = None
    from mkg.llm import reset_llm
    reset_llm()
