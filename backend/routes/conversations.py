"""
Conversation API routes
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.schemas import (
    ConversationBase, ConversationCreate, ConversationUpdate,
    ConversationDetail, MessageBase, MessageCreate
)
from mkg.database import Database

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

# Singleton database instance
_db = None


def get_db():
    global _db
    if _db is None:
        db_path = Path(__file__).parent.parent.parent / "mkg.db"
        _db = Database(str(db_path))
        _db.connect()
    return _db


@router.post("", response_model=ConversationBase)
def create_conversation(device_id: str = Header(None, alias="X-Device-ID")):
    """创建新对话"""
    db = get_db()
    if not device_id:
        raise HTTPException(status_code=400, detail="X-Device-ID header required")

    conv_id = db.create_conversation(device_id)
    return ConversationBase(id=conv_id, title=None)


@router.get("", response_model=List[ConversationBase])
def list_conversations(device_id: str = Header(None, alias="X-Device-ID")):
    """获取对话列表"""
    db = get_db()
    if not device_id:
        raise HTTPException(status_code=400, detail="X-Device-ID header required")

    conversations = db.get_conversations(device_id)
    return [ConversationBase(**c) for c in conversations]


@router.get("/{conv_id}", response_model=ConversationDetail)
def get_conversation(conv_id: str):
    """获取单个对话及其消息"""
    db = get_db()

    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.get_messages(conv_id)
    return ConversationDetail(
        id=conv['id'],
        title=conv['title'],
        created_at=conv['created_at'],
        updated_at=conv['updated_at'],
        messages=[MessageBase(**m) for m in messages]
    )


@router.put("/{conv_id}/title")
def update_title(conv_id: str, request: ConversationUpdate):
    """更新对话标题"""
    db = get_db()

    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.update_conversation_title(conv_id, request.title)
    return {"success": True}


@router.delete("/{conv_id}")
def delete_conversation(conv_id: str):
    """删除对话"""
    db = get_db()

    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete_conversation(conv_id)
    return {"success": True}


@router.post("/{conv_id}/messages")
def add_message(conv_id: str, request: MessageCreate):
    """添加消息到对话"""
    db = get_db()

    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.add_message(
        conv_id,
        request.role,
        request.content,
        request.agent,
        request.attachments
    )
    return {"success": True}