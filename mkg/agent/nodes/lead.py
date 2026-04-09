# mkg/agent/nodes/lead.py
"""
Lead Node - 统一对话节点

使用 MCP tools 或备用工具与 LLM 交互
"""

import re
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from typing import Dict, Any, Optional, List

from ..state import AgentState
from mkg.llm import get_llm_or_raise, extract_text_content
from .. import tools as legacy_tools

# Tool -> Attachment 类型映射
TOOL_ATTACHMENT_MAP = {
    "analyze_research_points": "research_points",
    "get_paper_by_title": "paper_detail",
    "search_paper": "paper_list",
    "get_concept_graph": "concept_graph",
    "analyze_citations": "citation_analysis",
    "recommend_papers": "recommendation",
    "deep_research": "deep_research",
}


def make_attachment(tool_name: str, result) -> Optional[Dict[str, Any]]:
    """将 tool 执行结果转换为附件"""
    att_type = TOOL_ATTACHMENT_MAP.get(tool_name)
    if not att_type:
        return None
    if isinstance(result, str):
        return None
    if isinstance(result, dict) and "error" in result:
        return None
    return {"type": att_type, "data": result}


def summarize_for_llm(tool_name: str, result) -> str:
    """生成给 LLM 的精简摘要，避免传入完整数据浪费 token

    多步工具编排：摘要需要足够丰富，帮助 LLM 决定是否需要下一步。
    """
    if isinstance(result, str):
        return result
    if isinstance(result, dict) and "error" in result:
        return f"错误: {result['error']}"

    if tool_name == "search_paper":
        count = result.get("count", 0)
        papers = result.get("papers", [])
        titles = [p.get("title", "?") for p in papers[:5]]
        summary = f"找到 {count} 篇论文：{', '.join(titles)}"
        if count > 5:
            summary += f"（还有 {count - 5} 篇）"
        return summary

    if tool_name == "get_paper_by_title":
        paper = result
        authors = ', '.join((paper.get('authors') or [])[:3])
        return f"论文：{paper.get('title', '?')}，作者：{authors}，年份：{paper.get('year', '?')}，摘要：{paper.get('abstract', '')[:100]}"

    if tool_name == "analyze_research_points":
        points = result.get("research_points", result.get("points", []))
        if isinstance(points, list):
            items = []
            for p in points[:3]:
                if isinstance(p, dict):
                    items.append(f"- {p.get('title', '?')}: {p.get('description', '')[:60]}")
                else:
                    items.append(f"- {p}")
            return f"发现 {len(points)} 个研究点：\n" + "\n".join(items)
        return f"研究点分析完成：{str(result)[:300]}"

    if tool_name == "get_concept_graph":
        children = result.get('children', [])
        parents = result.get('parents', [])
        child_names = ', '.join(c.get('name', '?') for c in children[:5])
        parent_names = ', '.join(p.get('name', '?') for p in parents[:3])
        parts = [f"概念「{result.get('name', '?')}」（{result.get('category', '')}）"]
        if parent_names:
            parts.append(f"父概念：{parent_names}")
        if child_names:
            parts.append(f"子概念：{child_names}")
        return f"已获取图谱数据：{'，'.join(parts)}"

    if tool_name == "analyze_citations":
        paper = result.get('paper', {})
        citations = result.get('citations', [])
        cited_by = result.get('cited_by', [])
        parts = [f"论文「{paper.get('title', '?')}」"]
        if citations:
            parts.append(f"引用了 {len(citations)} 篇论文：{', '.join(c.get('title', '?')[:30] for c in citations[:3])}")
        if cited_by:
            parts.append(f"被 {len(cited_by)} 篇论文引用：{', '.join(c.get('title', '?')[:30] for c in cited_by[:3])}")
        if not citations and not cited_by:
            parts.append("暂无引用数据")
        return f"引用分析：{'，'.join(parts)}"

    if tool_name == "recommend_papers":
        papers = result.get("papers", [])
        titles = [p.get("title", "?")[:40] for p in papers[:3]]
        return f"推荐 {len(papers)} 篇相关论文：{', '.join(titles)}"

    return str(result)[:500]


# Lead Node 系统提示
LEAD_SYSTEM_PROMPT = """你是 Meta Knowledge Graph 的研究助手。

【核心原则】
- 如果用户问题不需要工具，直接回答即可。
- 工具调用要精确匹配用户意图，不要"顺便"调用其他工具。
- 根据问题需要，可以依次调用多个工具完成研究。每次只调用一个工具，根据结果决定是否需要下一步。

【研究流程建议】
- 搜索论文 → 分析引用 → 综合回答
- 查看概念图谱 → 分析研究点 → 推荐论文
- 简单问题直接回答，不要调用工具
- 复杂问题可以分步研究，最多 5 步

【回复原则 - 非常重要】
- 调用工具后，数据会自动以卡片形式展示给用户
- 你只需要给出简短的引导性回复（1-2句话），不要重复数据内容
- 例如：调用 analyze_research_points 后，只需说"我分析了这个概念的研究点，请查看上方卡片"
- 例如：调用 search_paper 后，只需说"找到了相关论文，请查看上方列表"

【思考过程】
在回复用户前，你可以先进行内部思考，格式如下：
<think>
这里写你的思考过程、分析、推理...
</think>

思考过程会以折叠形式展示给用户，用户可以选择是否查看。

【工具选择规则】

用户说「有哪些论文」「搜索论文」→ 用 search_paper
用户说「研究点」「研究方向」「分析...的研究点」→ 用 analyze_research_points
用户说「查看图谱」「显示图谱」→ 用 get_concept_graph
用户说「引用」「被引用」「引用关系」→ 用 analyze_citations
用户说「论文内容」「这篇论文讲什么」→ 用 read_paper_content
用户说「推荐论文」「相关论文」「找相关工作」→ 用 recommend_papers

【禁止行为】
- 禁止在问「研究点」时同时调用 recommend_papers
- 禁止在问「图谱」时同时调用 analyze_research_points
- 禁止在问「论文」时同时调用 get_concept_graph
- 简单问答（如"你好"、"什么是XX"）不要调用任何工具
- 禁止在回复中重复工具返回的数据内容（数据已通过卡片展示）

【特别注意】
- 「查看...的研究点」要用 analyze_research_points，不要用 get_concept_graph！
- 只有用户明确说「图谱」两个字时才用 get_concept_graph
- 「推荐论文」「相关工作」要用 recommend_papers，不要用 search_paper

当前上下文：
{context_info}

请根据用户问题选择合适的工具，可以分步调用多个工具完成研究。"""


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
    Lead Node - 使用 LangChain tools 处理对话
    """
    llm = get_llm_or_raise()

    # 使用 LangChain 原生工具（更稳定）
    tools = legacy_tools.ALL_TOOLS

    llm_with_tools = llm.bind_tools(tools)

    # 构建消息
    context_info = build_context_info(state)
    system_prompt = LEAD_SYSTEM_PROMPT.format(context_info=context_info)

    messages = [SystemMessage(content=system_prompt)]
    messages.extend(state.get("messages", []))

    # 获取最后一条用户消息，用于工具选择验证
    last_user_msg = ""
    for msg in reversed(state.get("messages", [])):
        if hasattr(msg, 'content') and not hasattr(msg, 'type') or (hasattr(msg, 'type') and getattr(msg, 'type', '') != 'ai'):
            last_user_msg = msg.content if hasattr(msg, 'content') else str(msg)
            break

    # 调用 LLM
    response = llm_with_tools.invoke(messages)

    # 工具选择纠正逻辑
    if response.tool_calls:
        for i, tc in enumerate(response.tool_calls):
            tool_name = tc["name"]

            # 强制纠正：研究点相关查询必须用 analyze_research_points
            if tool_name == "get_concept_graph" and last_user_msg:
                research_keywords = ["研究点", "研究方向", "研究机会", "分析.*研究"]
                if any(re.search(kw, last_user_msg) for kw in research_keywords):
                    # 强制改为 analyze_research_points
                    response.tool_calls[i]["name"] = "analyze_research_points"
                    if "concept_name" not in response.tool_calls[i]["args"]:
                        # 从消息中提取概念名
                        response.tool_calls[i]["args"]["concept_name"] = last_user_msg.replace("研究点", "").replace("研究方向", "").replace("分析", "").strip()

    # 处理 tool calls — 循环处理直到 LLM 不再请求工具
    concept_data = None
    attachments: List[Dict[str, Any]] = []
    response_content = extract_text_content(response.content)
    tool_used = None  # 记录使用的工具
    max_tool_rounds = 5  # 防止无限循环

    round_count = 0
    while response.tool_calls and round_count < max_tool_rounds:
        round_count += 1
        tool_messages = []

        for tool_call in response.tool_calls:
            t_name = tool_call["name"]
            t_args = tool_call["args"]
            tool_used = t_name  # 记录最后使用的工具

            # 查找并执行工具
            for tool_item in tools:
                if tool_item.name == t_name:
                    try:
                        result = tool_item.invoke(t_args)

                        # 收集附件
                        attachment = make_attachment(t_name, result)
                        if attachment:
                            attachments.append(attachment)

                        # 特殊处理：get_concept_graph 返回图谱数据（向后兼容）
                        if t_name == "get_concept_graph" and isinstance(result, dict) and "id" in result:
                            concept_data = result

                        # 使用摘要给 LLM（节省 token）
                        summary = summarize_for_llm(t_name, result)
                        tool_messages.append(ToolMessage(
                            content=summary,
                            tool_call_id=tool_call["id"]
                        ))
                    except Exception as e:
                        tool_messages.append(ToolMessage(
                            content=f"错误: {str(e)}",
                            tool_call_id=tool_call["id"]
                        ))
                    break

        # 将本轮工具调用和结果添加到消息历史
        messages.append(response)
        messages.extend(tool_messages)

        # 继续调用 LLM（可能返回更多工具调用或最终回复）
        response = llm_with_tools.invoke(messages)
        response_content = extract_text_content(response.content)

    return {
        "response": response_content,
        "agent_used": "lead",
        "tool_used": tool_used,
        "needs_summary": False,
        "messages": [AIMessage(content=response_content)],
        "concept_data": concept_data,
        "attachments": attachments,
    }


def lead_node_stream(state: AgentState):
    """
    Lead Node 流式版本 - 用于 SSE 响应

    使用 generator 推送中间状态
    """
    llm = get_llm_or_raise()
    tools = legacy_tools.ALL_TOOLS
    llm_with_tools = llm.bind_tools(tools)

    # 构建消息
    context_info = build_context_info(state)
    system_prompt = LEAD_SYSTEM_PROMPT.format(context_info=context_info)
    messages = [SystemMessage(content=system_prompt)]
    messages.extend(state.get("messages", []))

    # 获取最后一条用户消息
    last_user_msg = ""
    for msg in reversed(state.get("messages", [])):
        if hasattr(msg, 'content') and not hasattr(msg, 'type') or (hasattr(msg, 'type') and getattr(msg, 'type', '') != 'ai'):
            last_user_msg = msg.content if hasattr(msg, 'content') else str(msg)
            break

    # 第一次 LLM 调用
    response = llm_with_tools.invoke(messages)

    # 工具选择纠正逻辑
    if response.tool_calls:
        for i, tc in enumerate(response.tool_calls):
            tool_name = tc["name"]
            if tool_name == "get_concept_graph" and last_user_msg:
                research_keywords = ["研究点", "研究方向", "研究机会", "分析.*研究"]
                if any(re.search(kw, last_user_msg) for kw in research_keywords):
                    response.tool_calls[i]["name"] = "analyze_research_points"
                    if "concept_name" not in response.tool_calls[i]["args"]:
                        response.tool_calls[i]["args"]["concept_name"] = last_user_msg.replace("研究点", "").replace("研究方向", "").replace("分析", "").strip()

    # 处理 tool calls — 循环处理直到 LLM 不再请求工具
    concept_data = None
    attachments: List[Dict[str, Any]] = []
    response_content = extract_text_content(response.content)
    max_tool_rounds = 5
    round_count = 0

    while response.tool_calls and round_count < max_tool_rounds:
        round_count += 1

        for tool_call in response.tool_calls:
            t_name = tool_call["name"]
            t_args = tool_call["args"]

            # 推送工具调用状态
            yield {"type": "tool_call", "tool_name": t_name}

            # 执行工具
            tool_messages = []
            for tool_item in tools:
                if tool_item.name == t_name:
                    try:
                        result = tool_item.invoke(t_args)

                        attachment = make_attachment(t_name, result)
                        if attachment:
                            attachments.append(attachment)

                        if t_name == "get_concept_graph" and isinstance(result, dict) and "id" in result:
                            concept_data = result

                        summary = summarize_for_llm(t_name, result)
                        tool_messages.append(ToolMessage(
                            content=summary,
                            tool_call_id=tool_call["id"]
                        ))
                    except Exception as e:
                        tool_messages.append(ToolMessage(
                            content=f"错误: {str(e)}",
                            tool_call_id=tool_call["id"]
                        ))
                    break

            # 推送工具完成状态
            yield {"type": "tool_result"}

            # 将本轮结果添加到消息历史
            messages.append(response)
            messages.extend(tool_messages)

            # 继续调用 LLM
            response = llm_with_tools.invoke(messages)
            response_content = extract_text_content(response.content)

    # 推送最终响应
    yield {
        "type": "response",
        "content": response_content,
        "attachments": attachments,
        "concept_data": concept_data,
    }