# mkg/agent/nodes/lead.py
"""
Lead Node - 统一对话节点

使用 MCP tools 与 LLM 交互
"""

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from typing import Dict, Any
import asyncio

from ..state import AgentState
from mkg.llm import get_llm_or_raise, extract_text_content

# MCP tools 加载
_mcp_tools = None


async def _load_mcp_tools():
    """加载 MCP tools"""
    global _mcp_tools
    if _mcp_tools is None:
        from langchain_mcp_adapters import load_mcp_tools
        from langchain_mcp_adapters.sessions import create_session

        # 连接到本地 MCP server (stdio)
        connection = {
            "transport": "stdio",
            "command": "python",
            "args": ["-m", "mkg.mcp_server"],
        }

        async with create_session(connection) as session:
            await session.initialize()
            _mcp_tools = await load_mcp_tools(session, connection=connection, server_name="mkg")

    return _mcp_tools


# Lead Node 系统提示 - 简化，让 MCP 工具描述发挥作用
LEAD_SYSTEM_PROMPT = """你是 Meta Knowledge Graph 的研究助手。

你可以使用以下工具：
- search_paper: 搜索论文（当用户问论文、找论文时使用）
- get_paper_by_title: 根据标题查找论文
- read_paper_content: 读取论文内容
- analyze_citations: 分析引用关系
- get_concept_graph: 显示概念图谱（仅当用户明确说「查看图谱」时使用）
- analyze_research_points: 分析研究点
- list_folders: 列出文件夹
- create_folder: 创建文件夹
- move_paper_to_folder: 移动论文到文件夹
- deep_research: 深入研究

当前上下文：
{context_info}

请根据用户问题选择合适的工具。"""


def build_context_info(state: AgentState) -> str:
    """构建上下文信息"""
    parts = []

    current_target = state.get("current_target")
    if current_target:
        type_label = "论文" if current_target.get("type") == "paper" else "概念"
        parts.append(f"正在关注：{type_label}「{current_target.get('name')}」")

    uploaded = state.get("uploaded_papers", [])
    if uploaded:
        titles = [p.get("title", "未知") for p in uploaded[-3:]]
        parts.append(f"最近上传：{', '.join(titles)}")

    if not parts:
        return "无特定上下文"

    return "\n".join(parts)


def lead_node(state: AgentState) -> Dict[str, Any]:
    """
    Lead Node - 使用 MCP tools 处理对话
    """
    llm = get_llm_or_raise()

    # 加载 MCP tools（同步方式）
    try:
        tools = asyncio.run(_load_mcp_tools())
    except Exception as e:
        # 如果 MCP 加载失败，使用旧的 LangChain tools
        print(f"MCP tools 加载失败: {e}, 使用备用工具")
        from .. import tools as legacy_tools
        tools = legacy_tools.ALL_TOOLS

    llm_with_tools = llm.bind_tools(tools)

    # 构建消息
    context_info = build_context_info(state)
    system_prompt = LEAD_SYSTEM_PROMPT.format(context_info=context_info)

    messages = [SystemMessage(content=system_prompt)]
    messages.extend(state.get("messages", []))

    # 调用 LLM
    response = llm_with_tools.invoke(messages)

    # 处理 tool calls
    concept_data = None
    response_content = extract_text_content(response.content)

    # 最多处理 5 轮工具调用
    max_iterations = 5
    iteration = 0

    while response.tool_calls and iteration < max_iterations:
        iteration += 1

        tool_messages = []
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # 查找并执行工具
            for tool_item in tools:
                if tool_item.name == tool_name:
                    try:
                        result = tool_item.invoke(tool_args)

                        # 特殊处理：get_concept_graph 返回图谱数据
                        if tool_name == "get_concept_graph" and isinstance(result, dict) and "id" in result:
                            concept_data = result
                            tool_messages.append(ToolMessage(
                                content=f"已获取概念「{result.get('name')}」的图谱数据",
                                tool_call_id=tool_call["id"]
                            ))
                        else:
                            tool_messages.append(ToolMessage(
                                content=str(result) if not isinstance(result, str) else result,
                                tool_call_id=tool_call["id"]
                            ))
                    except Exception as e:
                        tool_messages.append(ToolMessage(
                            content=f"错误: {str(e)}",
                            tool_call_id=tool_call["id"]
                        ))
                    break

        # 继续调用 LLM
        messages.append(response)
        messages.extend(tool_messages)
        response = llm_with_tools.invoke(messages)
        response_content = extract_text_content(response.content)

    return {
        "response": response_content,
        "agent_used": "lead",
        "needs_summary": False,
        "messages": [AIMessage(content=response_content)],
        "concept_data": concept_data,
    }