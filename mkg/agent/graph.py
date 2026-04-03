# mkg/agent/graph.py
"""
LangGraph Agent 图定义
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, Any

from .state import AgentState
from .routing import route_intent, needs_summary
from .tools import init_tools
from .llm_config import init_llm
from .nodes import lead_node, citation_node, research_node, paper_qa_node, summarize_node


# ============================================================
# 路由函数
# ============================================================

def route_by_intent(state: AgentState) -> str:
    """
    条件路由函数 - 根据意图决定下一步

    Args:
        state: 当前状态

    Returns:
        下一个节点名称或 END
    """
    intent = state.get("intent", "lead")

    if intent == "lead":
        return "end"  # lead 已直接回答，结束

    return intent


def check_needs_summary(state: AgentState) -> str:
    """
    检查是否需要汇总

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    if state.get("needs_summary", False):
        return "summarize"
    return END


# ============================================================
# Move Paper 节点（简单处理，不调用 LLM）
# ============================================================

def move_paper_node(state: AgentState) -> Dict[str, Any]:
    """
    Move Paper Node - 移动论文到文件夹（简单规则处理）
    """
    from langchain_core.messages import AIMessage
    from .tools import move_paper_to_folder, get_paper_by_title, _db

    target_name = state.get("target_name", "")
    message = state.get("messages", [])[-1].content if state.get("messages") else ""

    # 简单解析：从消息中提取文件夹名
    # 例如："移动到XX文件夹" -> "XX"
    folder_name = None
    for keyword in ["移动到", "放到", "移到", "放入", "归类到"]:
        if keyword in message:
            parts = message.split(keyword)
            if len(parts) > 1:
                folder_part = parts[1].strip()
                # 去掉可能的"文件夹"后缀
                folder_name = folder_part.replace("文件夹", "").strip()
                break

    if not folder_name:
        return {
            "response": "请告诉我要移动到哪个文件夹？",
            "agent_used": "lead",
            "needs_summary": False,
        }

    # 查找论文
    if _db:
        papers = _db.get_papers_by_status('processed')
        papers.extend(_db.get_papers_by_status('pending'))

        paper = None
        for p in papers:
            if target_name and target_name.lower() in (p.get('title') or '').lower():
                paper = p
                break

        if paper:
            result = move_paper_to_folder.invoke({
                "doi": paper['doi'],
                "folder_name": folder_name,
                "create_if_not_exist": True
            })
            return {
                "response": result,
                "agent_used": "lead",
                "needs_summary": False,
            }

    return {
        "response": f"未找到论文「{target_name}」，请确认论文名称。",
        "agent_used": "lead",
        "needs_summary": False,
    }


# ============================================================
# 图构建
# ============================================================

def build_agent_graph(db=None, s2_client=None, pdf_parser=None):
    """
    构建 LangGraph Agent 图

    Args:
        db: Database 实例
        s2_client: Semantic Scholar 客户端
        pdf_parser: PDF 解析器

    Returns:
        编译后的图
    """
    # 初始化 Tools 依赖
    init_tools(db=db, s2_client=s2_client, pdf_parser=pdf_parser)

    # 初始化 LLM 配置
    init_llm(db=db)

    # 创建图
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("lead", lead_node)
    graph.add_node("citation", citation_node)
    graph.add_node("research", research_node)
    graph.add_node("paper_qa", paper_qa_node)
    graph.add_node("move_paper", move_paper_node)
    graph.add_node("summarize", summarize_node)

    # 设置入口
    graph.set_entry_point("lead")

    # 条件路由：从 lead 根据意图分发
    graph.add_conditional_edges(
        "lead",
        route_by_intent,
        {
            "citation": "citation",
            "research": "research",
            "paper_qa": "paper_qa",
            "move_paper": "move_paper",
            "end": END,
        }
    )

    # 简单节点完成后检查是否需要汇总
    for node in ["citation", "research", "paper_qa"]:
        graph.add_conditional_edges(
            node,
            check_needs_summary,
            {
                "summarize": "summarize",
                END: END
            }
        )

    # move_paper 直接结束
    graph.add_edge("move_paper", END)

    # summarize 后结束
    graph.add_edge("summarize", END)

    # 添加记忆持久化
    memory = MemorySaver()

    return graph.compile(checkpointer=memory)


# ============================================================
# 单例管理
# ============================================================

_compiled_graph = None


def get_agent_graph(db=None, s2_client=None, pdf_parser=None):
    """
    获取编译后的 Agent 图（单例）

    Args:
        db: Database 实例
        s2_client: Semantic Scholar 客户端
        pdf_parser: PDF 解析器

    Returns:
        编译后的图
    """
    global _compiled_graph

    # 每次都重新初始化 LLM（确保配置正确）
    from .llm_config import init_llm
    init_llm(db=db)

    if _compiled_graph is None:
        _compiled_graph = build_agent_graph(db, s2_client, pdf_parser)

    return _compiled_graph


def reset_graph():
    """重置图（用于重新加载配置）"""
    global _compiled_graph
    _compiled_graph = None
    from .llm_config import reset_llm
    reset_llm()
    # 强制重新加载 routing 模块
    import importlib
    from . import routing
    importlib.reload(routing)