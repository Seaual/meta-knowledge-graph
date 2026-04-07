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
    """生成给 LLM 的精简摘要，避免传入完整数据浪费 token"""
    if isinstance(result, str):
        return result
    if isinstance(result, dict) and "error" in result:
        return f"错误: {result['error']}"

    if tool_name == "search_paper":
        count = result.get("count", 0)
        papers = result.get("papers", [])
        titles = [p.get("title", "?") for p in papers[:5]]
        return f"找到 {count} 篇论文：{', '.join(titles)}"

    if tool_name == "get_paper_by_title":
        return f"论文：{result.get('title', '?')}，作者：{', '.join((result.get('authors') or [])[:3])}，年份：{result.get('year', '?')}"

    if tool_name == "analyze_research_points":
        points = result.get("research_points", result.get("points", []))
        if isinstance(points, list):
            titles = [p.get("title", "?") if isinstance(p, dict) else str(p) for p in points[:5]]
            return f"发现 {len(points)} 个研究点：{', '.join(titles)}"
        return f"研究点分析完成：{str(result)[:200]}"

    if tool_name == "get_concept_graph":
        return f"已获取概念「{result.get('name', '?')}」的图谱数据"

    if tool_name == "analyze_citations":
        return f"论文「{result.get('paper', {}).get('title', '?')}」共有 {result.get('citation_count', 0)} 条引用"

    if tool_name == "recommend_papers":
        papers = result.get("papers", [])
        return f"推荐 {len(papers)} 篇相关论文"

    return str(result)[:500]


# Lead Node 系统提示
LEAD_SYSTEM_PROMPT = """你是 Meta Knowledge Graph 的研究助手。

【核心原则】
- 每次只调用一个工具！不要同时调用多个工具。
- 如果用户问题不需要工具，直接回答即可。
- 工具调用要精确匹配用户意图，不要"顺便"调用其他工具。

【工具选择规则】

用户说「有哪些论文」「搜索论文」→ 用 search_paper
用户说「研究点」「研究方向」「分析...的研究点」→ 用 analyze_research_points
用户说「查看图谱」「显示图谱」→ 用 get_concept_graph
用户说「引用」「被引用」→ 用 analyze_citations
用户说「论文内容」「这篇论文讲什么」→ 用 read_paper_content
用户说「推荐论文」「相关论文」「找相关工作」→ 用 recommend_papers

【禁止行为】
- 禁止在问「研究点」时同时调用 recommend_papers
- 禁止在问「图谱」时同时调用 analyze_research_points
- 禁止在问「论文」时同时调用 get_concept_graph
- 简单问答（如"你好"、"什么是XX"）不要调用任何工具

【特别注意】
- 「查看...的研究点」要用 analyze_research_points，不要用 get_concept_graph！
- 只有用户明确说「图谱」两个字时才用 get_concept_graph
- 「推荐论文」「相关工作」要用 recommend_papers，不要用 search_paper

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

    # 处理 tool calls
    concept_data = None
    attachments: List[Dict[str, Any]] = []
    response_content = extract_text_content(response.content)

    # 最多处理 5 轮工具调用（每轮只处理第一个 tool）
    max_iterations = 5
    iteration = 0

    while response.tool_calls and iteration < max_iterations:
        iteration += 1

        # 只处理第一个 tool call，防止 LLM 同时调用多个工具
        tool_call = response.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        # 查找并执行工具
        tool_messages = []
        for tool_item in tools:
            if tool_item.name == tool_name:
                try:
                    result = tool_item.invoke(tool_args)

                    # 收集附件
                    attachment = make_attachment(tool_name, result)
                    if attachment:
                        attachments.append(attachment)

                    # 特殊处理：get_concept_graph 返回图谱数据（向后兼容）
                    if tool_name == "get_concept_graph" and isinstance(result, dict) and "id" in result:
                        concept_data = result

                    # 使用摘要给 LLM（节省 token）
                    summary = summarize_for_llm(tool_name, result)
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
        "attachments": attachments,
    }