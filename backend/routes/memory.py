"""
Memory API routes -- user preference management and research memory retrieval
"""

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.schemas import MemoryCreate, MemoryResponse, PreferencesUpdate
from mkg.database import Database
from mkg.memory import AgentMemory

router = APIRouter(prefix="/api/memory", tags=["memory"])

_db = None


def get_db() -> Database:
    global _db
    if _db is None:
        db_path = Path(__file__).parent.parent.parent / "mkg.db"
        _db = Database(str(db_path))
        _db.connect()
    return _db


def get_memory() -> AgentMemory:
    return AgentMemory(get_db())


@router.get("/preferences")
def get_preferences():
    """Get all user preferences"""
    memory = get_memory()
    return memory.preferences.get_all()


@router.put("/preferences")
def update_preference(request: PreferencesUpdate):
    """Set a user preference"""
    memory = get_memory()
    memory.preferences.set(request.key, request.value)
    return {"success": True}


@router.delete("/preferences/{key}")
def delete_preference(key: str):
    """Delete a user preference"""
    memory = get_memory()
    if not memory.preferences.delete(key):
        raise HTTPException(status_code=404, detail="Preference not found")
    return {"success": True}


@router.get("/research/tags/{tags_str}")
def search_by_tags(tags_str: str):
    """Search research memories by comma-separated tags"""
    memory = get_memory()
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    results = memory.research.search_by_tags(tags)
    return results


@router.get("/research/concept/{concept_id}")
def search_by_concept(concept_id: str):
    """Search research memories by concept ID"""
    memory = get_memory()
    return memory.research.search_by_concept(concept_id)


@router.get("/research/type/{memory_type}")
def search_by_type(memory_type: str):
    """Search research memories by type"""
    memory = get_memory()
    return memory.research.search_by_type(memory_type)


@router.get("/research/paper/{paper_doi}")
def get_research_for_paper(paper_doi: str):
    """Get research memories related to a paper"""
    memory = get_memory()
    return memory.research.get_related(paper_doi)


@router.post("/research", response_model=MemoryResponse)
def add_research_memory(request: MemoryCreate):
    """Add a research memory"""
    memory = get_memory()
    mem_id = memory.research.add(
        title=request.title,
        content=request.content,
        memory_type=request.memory_type,
        tags=request.tags,
        concept_ids=request.concept_ids,
        paper_doi=request.paper_doi,
        source_section=request.source_section,
    )
    if not mem_id:
        raise HTTPException(status_code=400, detail="Failed to add memory")

    record = memory.research.get_by_id(mem_id)
    if not record:
        raise HTTPException(status_code=500, detail="Memory created but fetch failed")
    return record


@router.delete("/research/{mem_id}")
def delete_research_memory(mem_id: str):
    """Delete a research memory"""
    memory = get_memory()
    if not memory.research.delete(mem_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True}
