"""
Agent API routes
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.schemas import AgentChatRequest, AgentChatResponse, AgentMessage
from mkg.database import Database
from mkg.semantic_scholar import S2Client
from mkg.pdf_parser import PDFParser, LiteLLMClient

# LangGraph imports
from langchain_core.messages import HumanMessage, AIMessage

from mkg.agent.graph import get_agent_graph, reset_graph
from mkg.agent.routing import route_intent
from mkg.agent.state import AgentState

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Singleton instances
_db = None
_s2_client = None
_pdf_parser = None
_deep_research_agent = None


class DeepResearchStartRequest(BaseModel):
    targetId: str
    targetType: str
    targetName: str
    query: str
    dimensions: Optional[List[str]] = None


class DeepResearchStatusResponse(BaseModel):
    status: str
    progress: int
    dimensions: List[str]
    completedDimensions: List[str]


def get_db():
    global _db
    if _db is None:
        # 使用相对于项目根目录的路径
        db_path = Path(__file__).parent.parent.parent / "mkg.db"
        _db = Database(str(db_path))
        _db.connect()
    return _db


def get_s2_client():
    global _s2_client
    if _s2_client is None:
        _s2_client = S2Client()
    return _s2_client


def get_pdf_parser():
    global _pdf_parser
    if _pdf_parser is None:
        _pdf_parser = PDFParser()
    return _pdf_parser


def get_deep_research_agent():
    """获取 Deep Research Agent（保留原有实现）"""
    global _deep_research_agent
    if _deep_research_agent is None:
        db = get_db()
        config = db.get_llm_config()

        llm_client = None
        if config and config.get('providers'):
            provider_config = db.get_active_llm_provider()
            if not provider_config:
                provider_config = config['providers'][0]

            if provider_config:
                llm_client = LiteLLMClient(
                    provider=provider_config.get('provider'),
                    api_key=provider_config.get('api_key'),
                    model=provider_config.get('model'),
                    base_url=provider_config.get('base_url')
                )

        s2_client = get_s2_client()

        if llm_client:
            from mkg.agent.deep_research_agent import DeepResearchAgent
            _deep_research_agent = DeepResearchAgent(llm_client, db, s2_client)

    return _deep_research_agent


@router.post("/chat", response_model=AgentChatResponse)
def chat(request: AgentChatRequest):
    """
    处理用户对话 - 简化版

    所有请求都由 lead agent 处理，通过 tool 调用实现各种功能
    """
    # 检查 LLM 配置
    db = get_db()
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
    }

    # 执行图
    config = {"configurable": {"thread_id": "default"}}
    result = graph.invoke(initial_state, config)

    # 提取概念数据
    concept_data = result.get("concept_data")

    return AgentChatResponse(
        message=result.get("response", "抱歉，处理请求时遇到问题。"),
        agent=result.get("agent_used", "lead"),
        conceptData=concept_data,
    )


@router.post("/deep-research/start")
def start_deep_research(request: DeepResearchStartRequest):
    """启动深入研究任务"""
    agent = get_deep_research_agent()

    if not agent:
        raise HTTPException(
            status_code=500,
            detail="LLM 未配置，请先在设置中配置 API Key"
        )

    session_id = agent.start_research(
        target_type=request.targetType,
        target_id=request.targetId,
        target_name=request.targetName,
        query=request.query,
        dimensions=request.dimensions,
    )

    return {"sessionId": session_id, "status": "started"}


@router.get("/deep-research/{session_id}/status")
def get_research_status(session_id: str):
    """获取研究进度"""
    agent = get_deep_research_agent()

    if not agent:
        raise HTTPException(status_code=500, detail="Agent 未初始化")

    status = agent.get_status(session_id)

    if 'error' in status:
        raise HTTPException(status_code=404, detail=status['error'])

    return DeepResearchStatusResponse(**status)


@router.get("/deep-research/{session_id}/report")
def get_research_report(session_id: str):
    """获取研究报告"""
    agent = get_deep_research_agent()

    if not agent:
        raise HTTPException(status_code=500, detail="Agent 未初始化")

    report = agent.get_report(session_id)

    if 'error' in report:
        raise HTTPException(status_code=404, detail=report['error'])

    return report


@router.post("/reset")
def reset_agent():
    """重置 Agent 图（用于重新加载配置）"""
    # 强制重新加载所有 agent 模块
    import importlib
    from mkg.agent import routing, graph
    importlib.reload(routing)
    importlib.reload(graph)

    graph.reset_graph()
    return {"status": "ok"}