# mkg/agent/nodes/lead.py
"""
Lead Node - 通用对话节点
"""

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from typing import Dict, Any

from ..state import AgentState
from .. import tools  # 导入模块
from ..llm_config import get_llm_or_raise


# Lead Node 系统提示
LEAD_SYSTEM_PROMPT = """你是 Meta Knowledge Graph 的研究助手。

你可以帮助用户：
- 查看概念图谱：使用 get_concept_graph 工具获取图谱数据
- 分析论文引用关系（说"分析XX论文的引用"）
- 发现概念的研究机会（说"分析XX概念的研究点"）
- 深入研究主题（说"深入研究XX"）
- 回答论文内容问题（说"这篇论文讲了什么"）

当用户说"查看图谱"、"我的图谱"、"概念图谱"等，请调用 get_concept_graph 工具。

当前上下文：
{context_info}

请友好、简洁地回复用户。如果用户想使用特定功能但表述不清，可以引导他们更清楚地说明。"""


def build_context_info(state: AgentState) -> str:
    """构建上下文信息"""
    parts = []

    # 当前目标
    current_target = state.get("current_target")
    if current_target:
        type_label = "论文" if current_target.get("type") == "paper" else "概念"
        parts.append(f"正在关注：{type_label}「{current_target.get('name')}」")

    # 上传的论文
    uploaded = state.get("uploaded_papers", [])
    if uploaded:
        titles = [p.get("title", "未知") for p in uploaded[-3:]]
        parts.append(f"最近上传：{', '.join(titles)}")

    if not parts:
        return "无特定上下文"

    return "\n".join(parts)


def lead_node(state: AgentState) -> Dict[str, Any]:
    """
    Lead Node - 处理通用对话

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    # 获取 LLM
    llm = get_llm_or_raise()
    llm_with_tools = llm.bind_tools(tools.LEAD_TOOLS)

    # 构建消息
    context_info = build_context_info(state)
    system_prompt = LEAD_SYSTEM_PROMPT.format(context_info=context_info)

    messages = [SystemMessage(content=system_prompt)]
    messages.extend(state.get("messages", []))

    # 调用 LLM
    response = llm_with_tools.invoke(messages)

    # 处理 tool calls
    concept_data = None
    response_content = response.content

    if response.tool_calls:
        tool_messages = []
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # 查找并执行工具
            for tool_item in tools.LEAD_TOOLS:
                if tool_item.name == tool_name:
                    try:
                        result = tool_item.invoke(tool_args)
                        # 如果是 get_concept_graph，保存 concept_data
                        if tool_name == "get_concept_graph" and isinstance(result, dict) and "id" in result:
                            concept_data = result
                            tool_messages.append(ToolMessage(
                                content=f"已获取概念「{result.get('name')}」的图谱数据",
                                tool_call_id=tool_call["id"]
                            ))
                        else:
                            tool_messages.append(ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call["id"]
                            ))
                    except Exception as e:
                        tool_messages.append(ToolMessage(
                            content=f"错误: {str(e)}",
                            tool_call_id=tool_call["id"]
                        ))
                    break

        # 如果有工具调用，继续调用 LLM 生成最终响应
        if tool_messages:
            messages.append(response)
            messages.extend(tool_messages)
            final_response = llm_with_tools.invoke(messages)
            response_content = final_response.content

    return {
        "response": response_content,
        "agent_used": "lead",
        "needs_summary": False,
        "messages": [AIMessage(content=response_content)],
        "concept_data": concept_data,
    }