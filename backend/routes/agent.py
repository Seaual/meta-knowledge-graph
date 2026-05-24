"""Agent API routes — DeepAgents version."""

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage

from backend.dependencies import get_db, get_pdf_parser, get_s2_client
from backend.schemas import AgentChatRequest
from mkg.agent.agent import get_main_agent, reset_agent
from mkg.agent.streaming import convert_chunk_to_sse
from mkg.llm import init_llm_from_db

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat/stream")
async def chat_stream(request: AgentChatRequest):
    """Stream agent response via SSE."""
    db = get_db()
    init_llm_from_db(db)

    config = db.get_llm_config()
    if not config or not config.get("providers"):
        raise HTTPException(status_code=500, detail="LLM not configured")

    workspace_dir = f"data/agent_files/{request.conversationId or 'default'}"
    agent = get_main_agent(db_path="data/mkg.db", workspace_dir=workspace_dir)

    messages = []
    for m in request.history:
        if m.role == "user":
            messages.append(HumanMessage(content=m.content))
        else:
            messages.append(AIMessage(content=m.content))
    messages.append(HumanMessage(content=request.message))

    async def generate():
        try:
            yield f"data: {json.dumps({'type': 'status', 'status': 'thinking'})}\n\n"

            import asyncio
            loop = asyncio.get_event_loop()

            def _stream():
                return list(agent.stream(
                    {"messages": messages},
                    stream_mode=["updates", "messages", "custom"],
                    subgraphs=True,
                    version="v2",
                    config={"configurable": {
                        "thread_id": request.conversationId or "default",
                        "db": db,
                        "s2_client": get_s2_client(),
                        "pdf_parser": get_pdf_parser(),
                    }},
                ))

            chunks = await loop.run_in_executor(None, _stream)

            for chunk in chunks:
                event = convert_chunk_to_sse(chunk)
                if event:
                    yield f"data: {json.dumps(event)}\n\n"

            yield f"data: {json.dumps({'type': 'status', 'status': 'completed'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/approve")
async def approve_action(request: dict[str, Any]):
    """Approve a pending human-in-the-loop action."""
    return {"status": "approved"}


@router.post("/reset")
def reset_agent_route():
    """Reset agent singleton."""
    reset_agent()
    from mkg.llm import reset_llm
    reset_llm()
    return {"status": "ok"}
