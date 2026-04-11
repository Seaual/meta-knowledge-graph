"""
Agent API routes
"""

import json
import sys
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# LangGraph imports
from langchain_core.messages import AIMessage, HumanMessage

from backend.dependencies import get_db, get_pdf_parser, get_s2_client
from backend.schemas import AgentChatRequest, AgentChatResponse
from mkg.agent.graph import get_agent_graph, reset_graph
from mkg.agent.state import AgentState
from mkg.llm import init_llm_from_db, reset_llm

router = APIRouter(prefix="/api/agent", tags=["agent"])

# 工具名称中文映射
TOOL_LABELS = {
    "analyze_research_points": "分析研究点",
    "deep_research": "深入研究",
    "search_paper": "搜索论文",
    "get_paper_by_title": "获取论文详情",
    "read_paper_content": "阅读论文内容",
    "analyze_citations": "分析引用关系",
    "get_concept_graph": "获取概念图谱",
    "recommend_papers": "推荐相关论文",
}


def get_tool_label(tool_name: str) -> str:
    """获取工具的中文名称"""
    return TOOL_LABELS.get(tool_name, tool_name)


class DeepResearchStartRequest(BaseModel):
    targetId: str
    targetType: str
    targetName: str
    query: str
    dimensions: list[str] | None = None


class DeepResearchStatusResponse(BaseModel):
    status: str
    progress: int
    dimensions: list[str]
    completedDimensions: list[str]


@router.post("/chat", response_model=AgentChatResponse)
def chat(request: AgentChatRequest):
    """
    处理用户对话 - 简化版

    所有请求都由 lead agent 处理，通过 tool 调用实现各种功能
    """
    # 初始化 LLM
    db = get_db()
    init_llm_from_db(db)

    # 检查 LLM 配置
    config = db.get_llm_config()
    if not config or not config.get('providers'):
        raise HTTPException(
            status_code=500,
            detail="LLM 未配置，请先在设置中配置 API Key"
        )

    # 获取 LangGraph Agent
    graph = get_agent_graph(
        db=get_db(),
        s2_client=get_s2_client(),
        pdf_parser=get_pdf_parser()
    )

    # 构建消息历史
    messages = []
    for m in request.history:
        if m.role == "user":
            messages.append(HumanMessage(content=m.content))
        else:
            messages.append(AIMessage(content=m.content))

    # 添加当前消息
    messages.append(HumanMessage(content=request.message))

    # 构建初始状态
    initial_state: AgentState = {
        "messages": messages,
        "current_target": request.context.currentTarget if request.context else None,
        "uploaded_papers": request.context.uploadedPapers if request.context else [],
        "intent": "lead",
        "target_name": None,
        "response": "",
        "agent_used": "lead",
        "needs_summary": False,
        "attachments": [],
    }

    # 执行图
    config = {"configurable": {"thread_id": "default"}}
    result = graph.invoke(initial_state, config)

    # 提取概念数据（向后兼容）
    concept_data = result.get("concept_data")

    # 提取附件
    attachments = result.get("attachments", [])

    # 如果有 concept_data 但 attachments 中没有 concept_graph，自动迁移
    if concept_data and not any(a.get("type") == "concept_graph" for a in attachments):
        attachments.append({"type": "concept_graph", "data": concept_data})

    return AgentChatResponse(
        message=result.get("response", "抱歉，处理请求时遇到问题。"),
        agent=result.get("agent_used", "lead"),
        toolUsed=result.get("tool_used"),
        conceptData=concept_data,
        attachments=attachments,
    )


@router.post("/deep-research/start")
def start_deep_research(request: DeepResearchStartRequest):
    """启动深入研究任务（异步，后台运行）"""
    from mkg.agent.research_graph import get_deep_research_progress
    from mkg.agent.tools import deep_research

    # 生成唯一 session_id
    session_id = str(uuid.uuid4())[:12]

    init_llm_from_db(get_db())

    # 在后台线程运行
    def _run_research():
        try:
            deep_research.invoke({
                "target_name": request.targetName,
                "target_type": request.targetType,
                "query": request.query,
                "session_id": session_id,
            })
        except Exception as e:
            # 标记为错误状态
            progress = get_deep_research_progress(session_id)
            if progress:
                progress["status"] = "error"
                progress["error"] = str(e)

    thread = threading.Thread(target=_run_research, daemon=True)
    thread.start()

    return {
        "sessionId": session_id,
        "status": "running",
        "report": "",
        "dimensions": [],
    }


@router.get("/deep-research/{session_id}/status")
def get_deep_research_status(session_id: str):
    """获取深入研究任务状态"""
    from mkg.agent.research_graph import get_deep_research_progress

    progress = get_deep_research_progress(session_id)

    if not progress:
        raise HTTPException(status_code=404, detail="任务不存在")

    return progress


@router.get("/deep-research/{session_id}/report")
def get_deep_research_report(session_id: str):
    """获取深入研究任务报告"""
    from mkg.agent.research_graph import get_deep_research_progress

    progress = get_deep_research_progress(session_id)

    if not progress:
        raise HTTPException(status_code=404, detail="任务不存在")

    if progress.get("status") != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    return {
        "report": progress.get("report", ""),
        "dimensions": progress.get("dimensions", []),
    }


@router.post("/chat/stream")
async def chat_stream(request: AgentChatRequest):
    """
    处理用户对话 - SSE 流式响应版本

    推送 tool 状态，让前端显示动态进度
    """
    from mkg.agent.nodes.lead import lead_node_stream
    from mkg.agent.tools import init_tools

    db = get_db()
    init_llm_from_db(db)

    # 初始化 Tools 依赖
    init_tools(db=db, s2_client=get_s2_client(), pdf_parser=get_pdf_parser())

    # 检查 LLM 配置
    config = db.get_llm_config()
    if not config or not config.get('providers'):
        raise HTTPException(
            status_code=500,
            detail="LLM 未配置，请先在设置中配置 API Key"
        )

    # 构建消息历史
    messages = []
    for m in request.history:
        if m.role == "user":
            messages.append(HumanMessage(content=m.content))
        else:
            messages.append(AIMessage(content=m.content))

    messages.append(HumanMessage(content=request.message))

    # 构建初始状态
    initial_state: AgentState = {
        "messages": messages,
        "current_target": request.context.currentTarget if request.context else None,
        "uploaded_papers": request.context.uploadedPapers if request.context else [],
        "intent": "lead",
        "target_name": None,
        "response": "",
        "agent_used": "lead",
        "needs_summary": False,
        "attachments": [],
    }

    async def generate():
        """SSE 生成器"""
        try:
            # 推送开始状态
            yield f"data: {json.dumps({'type': 'status', 'status': 'thinking', 'message': '正在思考...'})}\n\n"

            # 调用流式 lead_node
            for event in lead_node_stream(initial_state):
                if event.get("type") == "tool_call":
                    # 推送工具调用状态
                    tool_name = event.get("tool_name", "")
                    yield f"data: {json.dumps({'type': 'tool', 'tool': tool_name, 'label': get_tool_label(tool_name), 'status': 'running'})}\n\n"
                elif event.get("type") == "tool_result":
                    # 推送工具完成状态
                    yield f"data: {json.dumps({'type': 'tool', 'status': 'completed'})}\n\n"
                elif event.get("type") == "response":
                    # 推送最终响应
                    yield f"data: {json.dumps({'type': 'response', 'message': event.get('content', ''), 'attachments': event.get('attachments', [])})}\n\n"

            # 推送完成状态
            yield f"data: {json.dumps({'type': 'status', 'status': 'completed'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/reset")
def reset_agent():
    """重置 Agent 图（用于重新加载配置）"""
    reset_llm()
    reset_graph()
    return {"status": "ok"}
