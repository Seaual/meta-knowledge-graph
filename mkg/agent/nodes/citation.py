# mkg/agent/nodes/citation.py
"""
Citation Node - 引用分析节点
"""

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from typing import Dict, Any

from ..state import AgentState
from ..tools import CITATION_TOOLS
from ..llm_config import get_llm_or_raise


CITATION_PROMPT = """分析论文「{target_name}」的引用关系。

请按以下步骤操作：
1. 使用 get_paper_by_doi 或 get_paper_by_title 获取论文信息
2. 使用 get_paper_citations 获取引用数据
3. 必要时使用 search_s2_papers 从 Semantic Scholar 补充数据

然后生成分析报告，包括：
- 被引统计（总数、年均、近年趋势）
- 高影响力引用者（引用数高的论文）
- 引用领域分布
- 关键洞察

请用中文回答，结构清晰。"""


def citation_node(state: AgentState) -> Dict[str, Any]:
    """
    Citation Node - 分析论文引用关系

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    llm = get_llm_or_raise()
    llm_with_tools = llm.bind_tools(CITATION_TOOLS)

    target_name = state.get("target_name", "未知论文")
    prompt = CITATION_PROMPT.format(target_name=target_name)

    # 构建消息
    messages = [HumanMessage(content=prompt)]

    # 调用 LLM
    response = llm_with_tools.invoke(messages)

    # 处理 tool calls 循环
    max_iterations = 5
    iteration = 0

    while response.tool_calls and iteration < max_iterations:
        iteration += 1

        # 收集工具调用结果
        tool_messages = []
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # 执行工具
            for tool in CITATION_TOOLS:
                if tool.name == tool_name:
                    try:
                        result = tool.invoke(tool_args)
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

        # 继续调用 LLM
        messages.append(response)
        messages.extend(tool_messages)
        response = llm_with_tools.invoke(messages)

    # 最终响应
    response_content = response.content

    return {
        "response": response_content,
        "agent_used": "citation",
        "needs_summary": len(response_content) > 1000,
        "messages": [AIMessage(content=response_content)],
    }