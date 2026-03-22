"""
Paper API routes
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import List, Optional
import sys
from pathlib import Path
import shutil
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from meta_knowledge_graph.database import Database
from meta_knowledge_graph.pdf_parser import PDFParser, LLMConceptExtractor, AnthropicClient, GoogleClient, OpenAICompatibleClient
from meta_knowledge_graph.graph import KnowledgeGraph
from .schemas import PaperResponse, PaperCreate, ProcessRequest, ProcessResponse

router = APIRouter(prefix="/api/papers", tags=["papers"])

# Global instances
_db = None
_graph = None
_parser = None
_extractor = None


def get_db():
    global _db
    if _db is None:
        _db = Database("openclaw.db")
        _db.connect()
    return _db


def get_graph():
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph(get_db())
    return _graph


def get_parser():
    global _parser
    if _parser is None:
        _parser = PDFParser()
    return _parser


def get_extractor():
    global _extractor
    if _extractor is None:
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            return None
        if os.getenv("ANTHROPIC_API_KEY"):
            client = AnthropicClient(api_key)
        elif os.getenv("GOOGLE_API_KEY"):
            client = GoogleClient(api_key)
        else:
            client = OpenAICompatibleClient(api_key)
        _extractor = LLMConceptExtractor(client)
    return _extractor


@router.get("/", response_model=List[PaperResponse])
def list_papers(status: Optional[str] = None):
    """Get all papers or filter by status"""
    db = get_db()
    if status:
        papers = db.get_papers_by_status(status)
    else:
        papers = db.get_all_papers()
    return papers


@router.get("/{doi:path}", response_model=PaperResponse)
def get_paper(doi: str):
    """Get a single paper by DOI"""
    db = get_db()
    paper = db.get_paper(doi)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.post("/upload")
async def upload_paper(file: UploadFile = File(...)):
    """Upload a PDF file"""
    # Create papers directory
    papers_dir = Path("papers")
    papers_dir.mkdir(exist_ok=True)

    # Save file
    file_path = papers_dir / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Parse PDF to get metadata
    parser = get_parser()
    content = parser.parse(str(file_path))

    if not content:
        raise HTTPException(status_code=400, detail="Failed to parse PDF")

    # Create paper record
    db = get_db()
    paper_data = {
        'doi': file.filename.replace('.pdf', ''),
        'title': content.title,
        'abstract': content.abstract,
        'authors': content.authors,
        'pdf_path': str(file_path),
    }
    doi = db.add_paper(paper_data)

    return {
        "success": True,
        "doi": doi,
        "title": content.title,
        "message": "Paper uploaded successfully"
    }


@router.post("/process", response_model=ProcessResponse)
def process_paper(request: ProcessRequest):
    """Process a paper with LLM extraction"""
    db = get_db()
    paper = db.get_paper(request.doi)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    pdf_path = paper.get('pdf_path')
    if not pdf_path or not Path(pdf_path).exists():
        raise HTTPException(status_code=400, detail="PDF file not found")

    # Get LLM extractor
    extractor = get_extractor()
    if not extractor:
        raise HTTPException(status_code=400, detail="LLM API not configured")

    # Parse and extract
    parser = get_parser()
    content = parser.parse(pdf_path)

    if not content:
        raise HTTPException(status_code=400, detail="Failed to parse PDF")

    try:
        extracted = extractor.extract(content)
        concept_tree = extracted.concept_tree.to_dict() if extracted.concept_tree else None

        if concept_tree:
            # Build graph
            graph = get_graph()
            graph.build_from_paper(request.doi, concept_tree)

            # Save extraction
            db.save_concept_extraction(request.doi, concept_tree, extracted.raw_response)

            return ProcessResponse(
                success=True,
                message="Paper processed successfully",
                concept_tree=concept_tree
            )
        else:
            return ProcessResponse(
                success=False,
                message="Failed to extract concepts"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{doi:path}")
def delete_paper(doi: str):
    """Delete a paper"""
    db = get_db()
    paper = db.get_paper(doi)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # Delete PDF file if exists
    pdf_path = paper.get('pdf_path')
    if pdf_path and Path(pdf_path).exists():
        Path(pdf_path).unlink()

    # Delete from database (cascade)
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM paper_concepts WHERE paper_doi = ?", (doi,))
    cursor.execute("DELETE FROM concept_extractions WHERE paper_doi = ?", (doi,))
    cursor.execute("DELETE FROM processing_log WHERE paper_doi = ?", (doi,))
    cursor.execute("DELETE FROM papers WHERE doi = ?", (doi,))
    db.conn.commit()

    return {"success": True, "message": "Paper deleted"}