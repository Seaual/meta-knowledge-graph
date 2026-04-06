# mkg/agent/nodes/lead.py
"""
Lead Node - 统一对话节点

所有功能都通过 tool 调用实现
"""

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from typing import Dict, Any

from ..state import AgentState
from .. import tools
from mkg.llm import get_llm_or_raise, extract_text_content


# Lead Node 系统提示
LEAD_SYSTEM_PROMPT = """你是 Meta Knowledge Graph 的研究助手。

你可以使用以下工具帮助用户：

**论文相关：**
- search_paper: 搜索论文
- get_paper_by_title: 根据标题查找论文
- read_paper_content: 读取论文 PDF 内容

**引用分析：**
- analyze_citations: 分析论文的引用关系

**概念相关：**
- get_concept_graph: 显示概念图谱可视化
- analyze_research_points: 分析概念的研究点

**文件夹管理：**
- list_folders: 列出所有文件夹
- move_paper_to_folder: 移动论文到文件夹
- create_folder: 创建新文件夹

---

**工具选择规则（非常重要）：**

用户问「有哪些论文」「搜索论文」「找论文」→ 用 search_paper
用户问「论文内容」「这篇论文讲什么」→ 用 read_paper_content
用户问「引用」「被引用」→ 用 analyze_citations
用户问「研究点」「研究方向」→ 用 analyze_research_points
用户明确说「查看图谱」「显示图谱」→ 用 get_concept_graph

**禁止使用 get_concept_graph 的场景：**
- 用户问论文列表、论文搜索 → 用 search_paper，不要用图谱！
- 用户问概念相关论文 → 用 search_paper，不要用图谱！

---

当前上下文：
{context_info}

请根据用户的问题选择合适的工具。回复要友好、简洁。"""


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
    Lead Node - 统一处理所有对话

    通过 tool 调用实现各种功能
    """
    llm = get_llm_or_raise()
    llm_with_tools = llm.bind_tools(tools.ALL_TOOLS)

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
            for tool_item in tools.ALL_TOOLS:
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