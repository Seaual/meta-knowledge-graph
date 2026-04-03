# mkg/agent/nodes/research.py
"""
Research Node - 研究点分析节点
"""

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from typing import Dict, Any, Optional

from ..state import AgentState
from .. import tools  # 导入模块而不是变量
from ..llm_config import get_llm_or_raise


RESEARCH_PROMPT = """分析概念「{target_name}」的研究机会。

请按以下步骤操作：
1. 使用 get_concept_info 获取概念信息
2. 使用 get_concept_papers 获取关联论文
3. 使用 search_s2_papers 搜索相关前沿工作

然后生成研究点分析，包括：
- 当前研究现状
- 概念的层级关系（父概念和子概念）
- 潜在研究方向（3-5个）
- 每个方向的研究价值和方法论建议
- 相关高引用论文推荐

请用中文回答，结构清晰。"""


def research_node(state: AgentState) -> Dict[str, Any]:
    """
    Research Node - 分析概念研究点

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    llm = get_llm_or_raise()
    llm_with_tools = llm.bind_tools(tools.RESEARCH_TOOLS)

    # 优先从 target_name 获取，其次从 current_target 获取
    target_name = state.get("target_name")
    current_target = state.get("current_target")

    if not target_name and current_target:
        # 从上下文目标获取
        if current_target.get("type") == "concept":
            target_name = current_target.get("name")
        elif current_target.get("type") == "paper":
            # 如果目标是论文，尝试获取论文的核心概念
            if tools._db:
                paper_doi = current_target.get("id")
                concepts = tools._db.get_concepts_by_paper(paper_doi) if paper_doi else []
                if concepts:
                    # 获取根概念或最相关的概念
                    target_name = concepts[0].get('text')

    # 如果还是没有目标，尝试获取数据库中的根概念
    if not target_name and tools._db:
        root_concepts = tools._db.get_root_concepts()
        if root_concepts:
            target_name = root_concepts[0].get('text')

    target_name = target_name or "未知概念"
    prompt = RESEARCH_PROMPT.format(target_name=target_name)

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
            for tool_item in tools.RESEARCH_TOOLS:
                if tool_item.name == tool_name:
                    try:
                        result = tool_item.invoke(tool_args)
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

    # 获取概念图谱数据（使用之前确定的 target_name）
    concept_data = None

    if target_name and target_name != "未知概念" and tools._db:
        # 尝试根据名称查找概念
        concept = tools._db.get_concept_by_text(target_name)
        if not concept:
            # 尝试模糊匹配
            all_concepts = tools._db.get_all_concepts()
            for c in all_concepts:
                if target_name.lower() in (c.get('text') or '').lower():
                    concept = c
                    break

        if concept:
            concept_id = concept['id']
            children = tools._db.get_concept_children(concept_id) or []
            parents = tools._db.get_concept_parents(concept_id) or []

            concept_data = {
                "id": concept_id,
                "name": concept.get('text', target_name),
                "category": concept.get('category'),
                "paper_count": concept.get('paper_count', 0),
                "children": [
                    {"id": c['id'], "name": c.get('text', ''), "paper_count": c.get('paper_count', 0)}
                    for c in children[:10]
                ],
                "parents": [
                    {"id": p['id'], "name": p.get('text', ''), "paper_count": p.get('paper_count', 0)}
                    for p in parents[:5]
                ],
            }

    return {
        "response": response_content,
        "agent_used": "research",
        "needs_summary": len(response_content) > 1000,
        "messages": [AIMessage(content=response_content)],
        "concept_data": concept_data,
    }