# mkg/agent/nodes/lead.py
"""
Lead Node - 通用对话节点
"""

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from typing import Dict, Any

from ..state import AgentState
from ..tools import LEAD_TOOLS
from ..llm_config import get_llm_or_raise


# Lead Node 系统提示
LEAD_SYSTEM_PROMPT = """你是 Meta Knowledge Graph 的研究助手。

你可以帮助用户：
- 分析论文引用关系（说"分析XX论文的引用"）
- 发现概念的研究机会（说"分析XX概念的研究点"）
- 深入研究主题（说"深入研究XX"）
- 回答论文内容问题（说"这篇论文讲了什么"）

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
    llm_with_tools = llm.bind_tools(LEAD_TOOLS)

    # 构建消息
    context_info = build_context_info(state)
    system_prompt = LEAD_SYSTEM_PROMPT.format(context_info=context_info)

    messages = [SystemMessage(content=system_prompt)]
    messages.extend(state.get("messages", []))

    # 调用 LLM
    response = llm_with_tools.invoke(messages)

    # 处理 tool calls
    if response.tool_calls:
        # 执行工具调用（简化处理，实际应该循环处理）
        tool_results = []
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # 查找并执行工具
            for tool in LEAD_TOOLS:
                if tool.name == tool_name:
                    try:
                        result = tool.invoke(tool_args)
                        tool_results.append(f"[{tool_name}] {result}")
                    except Exception as e:
                        tool_results.append(f"[{tool_name}] 错误: {str(e)}")
                    break

        # 将工具结果添加到响应
        if tool_results:
            response_content = response.content + "\n\n" + "\n".join(tool_results)
        else:
            response_content = response.content
    else:
        response_content = response.content

    return {
        "response": response_content,
        "agent_used": "lead",
        "needs_summary": False,
        "messages": [AIMessage(content=response_content)],
    }