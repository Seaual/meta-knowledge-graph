# mkg/agent/nodes/paper_qa.py
"""
Paper QA Node - 论文问答节点
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from mkg.llm import get_llm_or_raise

from ..state import AgentState
from ..tools import PAPER_QA_TOOLS

PAPER_QA_PROMPT = """回答关于论文「{target_name}」的问题：{question}

请按以下策略处理：
1. 先用 get_paper_by_title 获取论文元数据
2. 如果问题简单（摘要、作者、关键词、发表年份等），直接基于元数据回答
3. 如果问题复杂（方法、实验、结论、创新点等），使用 read_paper_content 读取全文后回答

回答要求：
- 准确：只基于论文内容回答，不要编造
- 简洁：回答清晰明了
- 注明来源：说明是基于摘要还是全文

请用中文回答。"""


# 简单问题关键词
SIMPLE_QUESTION_KEYWORDS = [
    "摘要", "作者", "关键词", "发表", "年份", "期刊",
    "会议", "标题", "是什么", "简介", "概述", "讲什么"
]


def is_simple_question(question: str) -> bool:
    """判断是否是简单问题"""
    return any(kw in question.lower() for kw in SIMPLE_QUESTION_KEYWORDS)


def paper_qa_node(state: AgentState) -> dict[str, Any]:
    """
    Paper QA Node - 回答论文内容问题

    Args:
        state: 当前状态

    Returns:
        状态更新
    """
    llm = get_llm_or_raise()
    llm_with_tools = llm.bind_tools(PAPER_QA_TOOLS)

    target_name = state.get("target_name", "未知论文")

    # 从消息历史提取问题
    messages = state.get("messages", [])
    question = messages[-1].content if messages else "这篇论文讲了什么？"

    prompt = PAPER_QA_PROMPT.format(target_name=target_name, question=question)

    # 构建消息
    invoke_messages = [HumanMessage(content=prompt)]

    # 调用 LLM
    response = llm_with_tools.invoke(invoke_messages)

    # 处理 tool calls 循环
    max_iterations = 3
    iteration = 0

    while response.tool_calls and iteration < max_iterations:
        iteration += 1

        # 收集工具调用结果
        tool_messages = []
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # 执行工具
            for tool in PAPER_QA_TOOLS:
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
        invoke_messages.append(response)
        invoke_messages.extend(tool_messages)
        response = llm_with_tools.invoke(invoke_messages)

    # 最终响应
    response_content = response.content

    # 添加来源标注
    source_note = "（基于论文全文）" if "read_paper_content" in str(response) else "（基于论文摘要）"

    return {
        "response": response_content + f"\n\n_{source_note}_",
        "agent_used": "paper_qa",
        "needs_summary": False,
        "messages": [AIMessage(content=response_content)],
    }
