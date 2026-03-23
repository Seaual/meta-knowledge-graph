"""
Paper API routes
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import List, Optional
from pydantic import BaseModel
import sys
from pathlib import Path
import shutil
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from openclaw.database import Database
from openclaw.pdf_parser import PDFParser, LLMConceptExtractor, AnthropicClient, GoogleClient, OpenAICompatibleClient, ClaudeCLIClient
from openclaw.graph import KnowledgeGraph
from backend.schemas import PaperResponse, PaperCreate, ProcessRequest, ProcessResponse, SkillConceptSubmission


class PaperMetadataUpdate(BaseModel):
    """论文元数据更新"""
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    contributions: Optional[List[str]] = None

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
        # 优先尝试使用 Claude CLI（利用 Claude Code 已配置的 API）
        try:
            _extractor = LLMConceptExtractor(ClaudeCLIClient())
            return _extractor
        except Exception as e:
            print(f"Claude CLI not available: {e}")

        # 回退到 API Key 方式
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
    """Upload a PDF file to pending folder"""
    import os

    # Create papers directory structure
    project_root = Path(__file__).parent.parent.parent
    pending_dir = project_root / "papers" / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    import time
    base_name = Path(file.filename).stem
    ext = Path(file.filename).suffix or ".pdf"
    unique_name = f"{base_name}_{int(time.time())}{ext}"
    file_path = pending_dir / unique_name

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Parse PDF to get metadata
    parser = get_parser()
    content = None
    try:
        content = parser.parse(str(file_path))
    except Exception as e:
        print(f"PDF 解析失败：{e}")

    # Create paper record
    db = get_db()

    if content and content.title:
        paper_data = {
            'doi': base_name,
            'title': content.title,
            'abstract': content.abstract or "",
            'authors': content.authors or [],
            'pdf_path': str(file_path),
        }
    else:
        # Fallback: use filename as title
        paper_data = {
            'doi': base_name,
            'title': base_name.replace('_', ' ').replace('-', ' '),
            'abstract': "",
            'authors': [],
            'pdf_path': str(file_path),
        }

    doi = db.add_paper(paper_data)

    return {
        "success": True,
        "doi": doi,
        "title": paper_data['title'],
        "pdf_path": str(file_path),
        "message": "Paper uploaded to pending folder"
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
        raise HTTPException(status_code=400, detail="LLM not configured. Claude CLI or API Key required.")

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


@router.post("/{doi:path}/concepts")
def submit_concepts(doi: str, submission: SkillConceptSubmission):
    """
    Skill 提交概念提取结果

    工作流程：
    1. Skill 读取 pending 文件夹中的 PDF
    2. 提取概念树
    3. 调用此 API 提交结果
    4. 系统保存概念树，移动文件到 processed 文件夹，更新状态
    """
    db = get_db()
    paper = db.get_paper(doi)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    pdf_path = paper.get('pdf_path')
    if not pdf_path:
        raise HTTPException(status_code=400, detail="PDF path not found in database")

    # Build graph from concept tree
    graph = get_graph()
    graph.build_from_paper(doi, submission.concept_tree)

    # Save extraction
    db.save_concept_extraction(doi, submission.concept_tree, submission.raw_response)

    # Move file from pending to processed
    pending_path = Path(pdf_path)
    if pending_path.exists():
        project_root = Path(__file__).parent.parent.parent
        processed_dir = project_root / "papers" / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)

        processed_path = processed_dir / pending_path.name

        # Move file
        import shutil
        shutil.move(str(pending_path), str(processed_path))

        # Update pdf_path in database
        cursor = db.conn.cursor()
        cursor.execute("UPDATE papers SET pdf_path = ? WHERE doi = ?", (str(processed_path), doi))
        db.conn.commit()

    # Update status to processed
    db.update_paper_status(doi, 'processed')

    return {
        "success": True,
        "message": "Concepts saved and paper moved to processed",
        "doi": doi
    }


@router.patch("/{doi:path}/metadata")
def update_paper_metadata(doi: str, update: PaperMetadataUpdate):
    """更新论文元数据（作者、摘要、关键词、创新点等）"""
    db = get_db()
    paper = db.get_paper(doi)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # 构建更新数据
    metadata = {}
    if update.title:
        metadata['title'] = update.title
    if update.abstract:
        metadata['abstract'] = update.abstract
    if update.authors:
        metadata['authors'] = update.authors
    if update.keywords:
        metadata['keywords'] = update.keywords
    if update.contributions:
        metadata['contributions'] = update.contributions

    if metadata:
        db.update_paper_metadata(doi, metadata)

    return {"success": True, "message": "Metadata updated", "doi": doi}


@router.get("/{doi:path}/text")
def get_paper_text(doi: str):
    """获取论文全文文本，供 Skill 分析使用"""
    db = get_db()
    paper = db.get_paper(doi)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    pdf_path = paper.get('pdf_path')
    if not pdf_path or not Path(pdf_path).exists():
        raise HTTPException(status_code=400, detail="PDF file not found")

    parser = get_parser()
    text = parser.extract_text(pdf_path)

    if not text:
        raise HTTPException(status_code=500, detail="Failed to extract text")

    return {"doi": doi, "text": text}


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