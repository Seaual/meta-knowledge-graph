"""
Agent API routes
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.schemas import AgentChatRequest, AgentChatResponse
from mkg.database import Database
from mkg.agent.lead_agent import LeadAgent
from mkg.agent.deep_research_agent import DeepResearchAgent
from mkg.semantic_scholar import S2Client
from mkg.pdf_parser import LiteLLMClient

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Singleton instances
_db = None
_lead_agent = None
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
        _db = Database("mkg.db")
        _db.connect()
    return _db


def get_lead_agent():
    global _lead_agent
    if _lead_agent is None:
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

        if llm_client:
            _lead_agent = LeadAgent(llm_client, db)

    return _lead_agent


def get_deep_research_agent():
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

        s2_client = S2Client()

        if llm_client:
            _deep_research_agent = DeepResearchAgent(llm_client, db, s2_client)

    return _deep_research_agent


@router.post("/chat", response_model=AgentChatResponse)
def chat(request: AgentChatRequest):
    """
    处理用户对话

    1. Lead Agent 识别意图
    2. 根据意图分发到专业 Agent
    3. 返回响应
    """
    lead_agent = get_lead_agent()

    if not lead_agent:
        raise HTTPException(
            status_code=500,
            detail="LLM 未配置，请先在设置中配置 API Key"
        )

    # 识别意图并生成响应
    context_dict = request.context.model_dump()
    result = lead_agent.generate_response(request.message, context_dict)

    # 如果有意图结果，表示需要分发到专业 Agent
    if 'intent_result' in result:
        intent_result = result['intent_result']
        intent = intent_result['intent']
        target_name = intent_result.get('target_name')

        # 分发到 Citation Agent
        if intent == 'citation' and target_name:
            citation_result = lead_agent.dispatch_to_citation_agent(target_name, context_dict)
            return AgentChatResponse(
                message=citation_result['message'],
                agent=citation_result['agent'],
                contextUpdate=citation_result.get('contextUpdate')
            )

        # 分发到 Research Agent
        if intent == 'research' and target_name:
            research_result = lead_agent.dispatch_to_research_agent(target_name, context_dict)
            return AgentChatResponse(
                message=research_result['message'],
                agent=research_result['agent'],
                contextUpdate=research_result.get('contextUpdate')
            )

        # 分发到 Deep Research Agent
        if intent == 'deep_research' and target_name:
            target_type = intent_result.get('target_type', 'concept')
            target_id = target_name  # 简化处理

            deep_result = lead_agent.dispatch_to_deep_research(
                target_name, target_type, target_id, request.message, context_dict
            )
            return AgentChatResponse(
                message=deep_result['message'],
                agent=deep_result['agent'],
                contextUpdate=deep_result.get('contextUpdate'),
                researchSessionId=deep_result.get('researchSessionId')
            )

        # 其他 Agent 待实现
        return AgentChatResponse(
            message=f"我理解您想要{intent_result['reasoning']}。该功能即将上线！",
            agent=intent_result['intent'],
            contextUpdate=None
        )

    return AgentChatResponse(
        message=result['message'],
        agent=result['agent'],
        contextUpdate=result.get('contextUpdate')
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