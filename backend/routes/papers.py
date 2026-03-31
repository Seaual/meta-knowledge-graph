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
import asyncio
import uuid
import time
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mkg.database import Database
from mkg.pdf_parser import PDFParser, LLMConceptExtractor, ClaudeCLIClient, LiteLLMClient
from mkg.graph import KnowledgeGraph
from mkg.semantic_scholar import S2Client
from backend.schemas import PaperResponse, PaperCreate, ProcessRequest, ProcessResponse, SkillConceptSubmission, BatchProcessRequest


class PaperMetadataUpdate(BaseModel):
    """论文元数据更新"""
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    contributions: Optional[List[str]] = None


class MovePaperRequest(BaseModel):
    """移动论文到文件夹"""
    folder_id: str = "default"

router = APIRouter(prefix="/api/papers", tags=["papers"])

# Global instances
_db = None
_graph = None
_parser = None
_extractor = None


def get_db():
    global _db
    if _db is None:
        _db = Database("mkg.db")
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
        db = get_db()

        # Try database config first
        config = db.get_llm_config()
        if config and config.get('providers'):
            provider_config = None
            if config['mode'] == 'per_function':
                # For papers, use paper_parsing or default to first
                provider_config = db.get_llm_provider_for_function('paper_parsing')
                if not provider_config:
                    provider_config = config['providers'][0]
            else:
                provider_config = db.get_active_llm_provider()
                if not provider_config:
                    provider_config = config['providers'][0]

            if provider_config:
                _extractor = _create_client_from_config(provider_config)
                return _extractor

        # Fallback to environment variables
        _extractor = _create_client_from_env()
        return _extractor
    return _extractor


def _create_client_from_config(config: dict):
    """Create LLM client from database config using LiteLLM"""
    provider = config.get('provider')
    api_key = config.get('api_key')
    base_url = config.get('base_url')
    model = config.get('model')

    if provider == 'claude_cli':
        return LLMConceptExtractor(ClaudeCLIClient())

    # 所有其他服务商通过 LiteLLM 统一处理
    return LLMConceptExtractor(LiteLLMClient(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url
    ))


def _create_client_from_env():
    """Create LLM client from environment variables using LiteLLM"""
    # 检查各种 API Key 环境变量
    for provider, env_key in LiteLLMClient.ENV_KEY_MAP.items():
        api_key = os.getenv(env_key)
        if api_key:
            return LLMConceptExtractor(LiteLLMClient(provider=provider, api_key=api_key))
    return None


# Semantic Scholar API Key（硬编码）
S2_API_KEY = "HdvhTeK6be5JUDCMKhwXa66QibQ2Qn171FL0Kkns"


def get_s2_client():
    """获取 Semantic Scholar 客户端"""
    return S2Client(api_key=S2_API_KEY)


@router.get("/", response_model=List[PaperResponse])
def list_papers(status: Optional[str] = None, folder: Optional[str] = None):
    """Get all papers or filter by status/folder"""
    db = get_db()

    if folder:
        papers = db.get_papers_by_folder(folder)
        if status:
            papers = [p for p in papers if p.get('status') == status]
    elif status:
        papers = db.get_papers_by_status(status)
    else:
        papers = db.get_all_papers()

    # Ensure list fields are not None
    for p in papers:
        if p.get('keywords') is None:
            p['keywords'] = []
        if p.get('contributions') is None:
            p['contributions'] = []
        if p.get('authors') is None:
            p['authors'] = []
        if p.get('s2_fields_of_study') is None:
            p['s2_fields_of_study'] = []

    return papers


@router.get("/by-folder/{folder_id}")
def get_papers_by_folder(folder_id: str):
    """Get papers by folder - specific route before general {doi:path}"""
    db = get_db()
    papers = db.get_papers_by_folder(folder_id)
    # Ensure list fields are not None
    for p in papers:
        if p.get('keywords') is None:
            p['keywords'] = []
        if p.get('contributions') is None:
            p['contributions'] = []
        if p.get('authors') is None:
            p['authors'] = []
    return papers


@router.post("/upload")
async def upload_paper(file: UploadFile = File(...), folder: str = Form("default")):
    """Upload a PDF file to pending folder"""
    # Create papers directory structure
    project_root = Path(__file__).parent.parent.parent
    pending_dir = project_root / "papers" / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    import time
    # Sanitize filename to prevent path traversal
    safe_filename = Path(file.filename).name
    base_name = Path(safe_filename).stem
    ext = Path(safe_filename).suffix or ".pdf"
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

    # Semantic Scholar 元数据增强 - 跳过以避免上传卡住
    # S2 匹配会在"处理"阶段进行，上传时跳过
    # s2_client = get_s2_client()
    # if s2_client and paper_data.get('title'):
    #     try:
    #         s2_data = s2_client.match_paper_by_title(paper_data['title'])
    #         ...
    #     except Exception as e:
    #         print(f"S2 enhancement failed: {e}")

    doi = db.add_paper(paper_data)

    # Update paper with folder
    if folder != "default":
        db.move_paper_to_folder(doi, folder)

    return {
        "success": True,
        "doi": doi,
        "title": paper_data['title'],
        "pdf_path": str(file_path),
        "message": "Paper uploaded to pending folder",
        "folder": folder
    }


@router.post("/batch-upload")
async def batch_upload_papers(files: List[UploadFile] = File(...)):
    """批量上传多个 PDF 文件"""
    project_root = Path(__file__).parent.parent.parent
    pending_dir = project_root / "papers" / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    job_id = f"batch_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    uploaded = []

    db = get_db()

    for file in files:
        if not file.filename or not file.filename.endswith('.pdf'):
            uploaded.append({
                "filename": file.filename or "unknown",
                "success": False,
                "error": "Invalid file type"
            })
            continue

        safe_filename = Path(file.filename).name
        base_name = Path(safe_filename).stem
        ext = Path(safe_filename).suffix
        unique_name = f"{base_name}_{int(time.time())}_{uuid.uuid4().hex[:4]}{ext}"
        file_path = pending_dir / unique_name

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            parser = get_parser()
            content = await asyncio.to_thread(parser.parse, str(file_path))

            if content and content.title:
                paper_data = {
                    'doi': base_name,
                    'title': content.title,
                    'abstract': content.abstract or "",
                    'authors': content.authors or [],
                    'pdf_path': str(file_path),
                }
            else:
                paper_data = {
                    'doi': base_name,
                    'title': base_name.replace('_', ' ').replace('-', ' '),
                    'abstract': "",
                    'authors': [],
                    'pdf_path': str(file_path),
                }

            # Semantic Scholar 元数据增强
            s2_client = get_s2_client()
            if s2_client and paper_data.get('title'):
                try:
                    s2_data = s2_client.match_paper_by_title(paper_data['title'])
                    if s2_data:
                        external_ids = s2_data.get('externalIds', {})
                        s2_doi = external_ids.get('DOI') if external_ids else None
                        open_access_pdf_url = s2_data.get('openAccessPdf')
                        tldr = s2_data.get('tldr')
                        fields_of_study = s2_data.get('s2FieldsOfStudy', [])

                        paper_data['s2_paper_id'] = s2_data.get('paperId')
                        paper_data['s2_doi'] = s2_doi
                        paper_data['citation_count'] = s2_data.get('citationCount', 0)
                        paper_data['reference_count'] = s2_data.get('referenceCount', 0)
                        paper_data['influential_citation_count'] = s2_data.get('influentialCitationCount', 0)
                        paper_data['venue'] = s2_data.get('venue')
                        paper_data['year'] = s2_data.get('year')
                        paper_data['tldr'] = tldr
                        paper_data['s2_fields_of_study'] = json.dumps(fields_of_study) if fields_of_study else None
                        paper_data['open_access_pdf_url'] = open_access_pdf_url
                        paper_data['s2_matched_at'] = datetime.now().isoformat()

                        if s2_data.get('abstract') and not paper_data.get('abstract'):
                            paper_data['abstract'] = s2_data['abstract']
                        if s2_data.get('authors') and not paper_data.get('authors'):
                            paper_data['authors'] = [a.get('name') for a in s2_data['authors'] if a.get('name')]
                except Exception as e:
                    print(f"S2 enhancement failed: {e}")

            doi = db.add_paper(paper_data)
            uploaded.append({
                "doi": doi,
                "title": paper_data['title'],
                "filename": file.filename,
                "status": "pending",
                "success": True
            })
        except Exception as e:
            uploaded.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })

    successful_uploads = [u for u in uploaded if u.get('success')]
    db.create_batch_job(job_id, len(successful_uploads))

    return {
        "job_id": job_id,
        "uploaded": uploaded,
        "total": len(successful_uploads)
    }


@router.post("/batch-process")
async def batch_process_papers(request: BatchProcessRequest):
    """并行处理多个论文（分批处理，包含 S2 匹配）"""
    db = get_db()
    parser = get_parser()
    extractor = get_extractor()

    if not extractor:
        raise HTTPException(status_code=400, detail="LLM not configured")

    # 如果 job 不存在，自动创建
    job = db.get_batch_job(request.job_id)
    if not job:
        db.create_batch_job(request.job_id, len(request.dois))
        job = db.get_batch_job(request.job_id)

    db.update_batch_job(request.job_id, 0, 0, 0, 'processing')

    completed = 0
    successful = 0
    failed = 0
    results = []

    async def process_single(doi: str) -> dict:
        try:
            paper = db.get_paper(doi)
            if not paper or not paper.get('pdf_path'):
                return {"doi": doi, "status": "failed", "error": "Paper or PDF not found"}

            content = await asyncio.to_thread(parser.parse, paper['pdf_path'])
            if not content:
                return {"doi": doi, "status": "failed", "error": "Failed to parse PDF"}

            # Get existing concepts for smart matching
            graph = get_graph()
            existing_concepts = graph.get_concept_tree_summary()

            extracted = await asyncio.to_thread(extractor.extract, content, existing_concepts)
            if extracted.concept_tree:
                graph.build_from_paper(doi, extracted.concept_tree.to_dict())
                db.save_concept_extraction(doi, extracted.concept_tree.to_dict(), extracted.raw_response)
                db.update_paper_status(doi, 'processed')

                # S2 匹配和引用构建
                s2_client = get_s2_client()
                if s2_client and paper.get('title'):
                    try:
                        s2_data = s2_client.match_paper_by_title(paper['title'])
                        if s2_data:
                            external_ids = s2_data.get('externalIds', {})
                            s2_doi = external_ids.get('DOI') if external_ids else None
                            s2_paper_id = s2_data.get('paperId')

                            metadata_update = {
                                's2_paper_id': s2_paper_id,
                                's2_doi': s2_doi,
                                'citation_count': s2_data.get('citationCount', 0),
                                'reference_count': s2_data.get('referenceCount', 0),
                                'venue': s2_data.get('venue'),
                                'year': s2_data.get('year'),
                                'tldr': s2_data.get('tldr'),
                                's2_matched_at': datetime.now().isoformat(),
                            }
                            db.update_paper_metadata(doi, metadata_update)

                            # 构建引用关系
                            if s2_paper_id:
                                references = s2_client.get_paper_references(s2_paper_id, limit=50)
                                for ref in references:
                                    ref_s2_id = ref.get('paperId')
                                    if not ref_s2_id:
                                        continue
                                    citation_data = {
                                        'citing_paper_id': doi,
                                        'cited_paper_id': ref_s2_id,
                                        'citing_s2_id': s2_paper_id,
                                        'cited_s2_id': ref_s2_id,
                                        'citing_title': paper.get('title'),
                                        'citing_year': paper.get('year'),
                                        'cited_title': ref.get('title'),
                                        'cited_year': ref.get('year'),
                                        'cited_citation_count': ref.get('citationCount', 0),
                                        'is_internal': False
                                    }
                                    db.add_paper_citation(citation_data)
                    except Exception as e:
                        print(f"S2 matching failed for {doi}: {e}")

                return {"doi": doi, "status": "success", "concepts": len(extracted.concept_tree.children) if extracted.concept_tree.children else 0}
            else:
                return {"doi": doi, "status": "failed", "error": "No concepts extracted"}
        except Exception as e:
            return {"doi": doi, "status": "failed", "error": str(e)}

    # 每 5 个一批处理
    batch_size = 5

    for i in range(0, len(request.dois), batch_size):
        batch = request.dois[i:i + batch_size]
        batch_results = await asyncio.gather(*[process_single(doi) for doi in batch])

        for result in batch_results:
            results.append(result)
            completed += 1
            if result["status"] == "success":
                successful += 1
            else:
                failed += 1

        # 更新进度
        db.update_batch_job(request.job_id, completed, successful, failed,
                          'completed' if completed == len(request.dois) else 'processing')

    return {
        "job_id": request.job_id,
        "status": "completed",
        "total": len(request.dois),
        "completed": completed,
        "successful": successful,
        "failed": failed,
        "results": results
    }


@router.get("/batch-status/{job_id}")
def get_batch_status(job_id: str):
    """获取批量任务状态"""
    db = get_db()
    job = db.get_batch_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found")
    return job


@router.post("/process", response_model=ProcessResponse)
def process_paper(request: ProcessRequest):
    """Process a paper with LLM extraction, S2 metadata, and citation building"""
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

    # Get existing concepts for smart matching
    graph = get_graph()
    existing_concepts = graph.get_concept_tree_summary()

    # Parse and extract
    parser = get_parser()
    content = parser.parse(pdf_path)

    if not content:
        raise HTTPException(status_code=400, detail="Failed to parse PDF")

    try:
        extracted = extractor.extract(content, existing_concepts)
        concept_tree = extracted.concept_tree.to_dict() if extracted.concept_tree else None

        if concept_tree:
            # Build graph (already initialized above)
            graph.build_from_paper(request.doi, concept_tree)

            # Save extraction
            db.save_concept_extraction(request.doi, concept_tree, extracted.raw_response)

            # Perform S2 metadata matching and citation building
            s2_client = get_s2_client()
            if s2_client and paper.get('title'):
                try:
                    s2_data = s2_client.match_paper_by_title(paper['title'])
                    if s2_data:
                        external_ids = s2_data.get('externalIds', {})
                        s2_doi = external_ids.get('DOI') if external_ids else None
                        s2_paper_id = s2_data.get('paperId')

                        # Update paper with S2 metadata
                        metadata_update = {
                            's2_paper_id': s2_paper_id,
                            's2_doi': s2_doi,
                            'citation_count': s2_data.get('citationCount', 0),
                            'reference_count': s2_data.get('referenceCount', 0),
                            'influential_citation_count': s2_data.get('influentialCitationCount', 0),
                            'venue': s2_data.get('venue'),
                            'year': s2_data.get('year'),
                            'tldr': s2_data.get('tldr'),
                            's2_fields_of_study': json.dumps(s2_data.get('s2FieldsOfStudy', [])),
                            'open_access_pdf_url': s2_data.get('openAccessPdf'),
                            's2_matched_at': datetime.now().isoformat(),
                        }
                        db.update_paper_metadata(request.doi, metadata_update)

                        # Build citation relationships
                        if s2_paper_id:
                            existing_papers = db.get_papers_with_s2_id()
                            s2_to_doi = {p['s2_paper_id']: p['doi'] for p in existing_papers if p.get('s2_paper_id')}

                            # Get references
                            try:
                                references = s2_client.get_paper_references(s2_paper_id, limit=50)
                                for ref in references:
                                    ref_s2_id = ref.get('paperId')
                                    if not ref_s2_id:
                                        continue
                                    is_internal = ref_s2_id in s2_to_doi
                                    citation_data = {
                                        'citing_paper_id': request.doi,
                                        'cited_paper_id': s2_to_doi.get(ref_s2_id, ref_s2_id),
                                        'citing_s2_id': s2_paper_id,
                                        'cited_s2_id': ref_s2_id,
                                        'citing_title': paper.get('title'),
                                        'citing_year': paper.get('year'),
                                        'cited_title': ref.get('title'),
                                        'cited_year': ref.get('year'),
                                        'cited_citation_count': ref.get('citationCount', 0),
                                        'is_internal': is_internal
                                    }
                                    db.add_paper_citation(citation_data)
                            except Exception as e:
                                print(f"Failed to get references: {e}")

                            # Get citations
                            try:
                                citations = s2_client.get_paper_citations(s2_paper_id, limit=50)
                                for cit in citations:
                                    cit_s2_id = cit.get('paperId')
                                    if not cit_s2_id:
                                        continue
                                    is_internal = cit_s2_id in s2_to_doi
                                    citation_data = {
                                        'citing_paper_id': s2_to_doi.get(cit_s2_id, cit_s2_id),
                                        'cited_paper_id': request.doi,
                                        'citing_s2_id': cit_s2_id,
                                        'cited_s2_id': s2_paper_id,
                                        'citing_title': cit.get('title'),
                                        'citing_year': cit.get('year'),
                                        'cited_title': paper.get('title'),
                                        'cited_year': paper.get('year'),
                                        'cited_citation_count': s2_data.get('citationCount', 0),
                                        'is_internal': is_internal
                                    }
                                    db.add_paper_citation(citation_data)
                            except Exception as e:
                                print(f"Failed to get citations: {e}")

                except Exception as e:
                    print(f"S2 matching failed for {request.doi}: {e}")

            return ProcessResponse(
                success=True,
                message="Paper processed successfully with S2 metadata and citations",
                concept_tree=concept_tree
            )
        else:
            return ProcessResponse(
                success=False,
                message="Failed to extract concepts"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-single")
async def process_single_paper(request: ProcessRequest):
    """
    Process a single paper and return duration for time estimation.

    Same logic as /process but adds duration and concepts_count to response.
    Also performs S2 metadata matching and builds citation relationships.
    """
    start_time = time.time()

    db = get_db()
    paper = db.get_paper(request.doi)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    pdf_path = paper.get('pdf_path')
    if not pdf_path or not Path(pdf_path).exists():
        raise HTTPException(status_code=400, detail="PDF file not found")

    extractor = get_extractor()
    if not extractor:
        raise HTTPException(status_code=400, detail="LLM not configured. Claude CLI or API Key required.")

    graph = get_graph()
    existing_concepts = graph.get_concept_tree_summary()

    parser = get_parser()
    content = parser.parse(pdf_path)

    if not content:
        raise HTTPException(status_code=400, detail="Failed to parse PDF")

    try:
        extracted = extractor.extract(content, existing_concepts)
        concept_tree = extracted.concept_tree.to_dict() if extracted.concept_tree else None

        if concept_tree:
            graph.build_from_paper(request.doi, concept_tree)
            db.save_concept_extraction(request.doi, concept_tree, extracted.raw_response)

            # Perform S2 metadata matching and citation building
            s2_client = get_s2_client()
            s2_data = None
            citation_count = 0

            if s2_client and paper.get('title'):
                try:
                    s2_data = s2_client.match_paper_by_title(paper['title'])
                    if s2_data:
                        external_ids = s2_data.get('externalIds', {})
                        s2_doi = external_ids.get('DOI') if external_ids else None
                        s2_paper_id = s2_data.get('paperId')
                        open_access_pdf_url = s2_data.get('openAccessPdf')
                        tldr = s2_data.get('tldr')
                        fields_of_study = s2_data.get('s2FieldsOfStudy', [])

                        # Update paper with S2 metadata
                        metadata_update = {
                            's2_paper_id': s2_paper_id,
                            's2_doi': s2_doi,
                            'citation_count': s2_data.get('citationCount', 0),
                            'reference_count': s2_data.get('referenceCount', 0),
                            'influential_citation_count': s2_data.get('influentialCitationCount', 0),
                            'venue': s2_data.get('venue'),
                            'year': s2_data.get('year'),
                            'tldr': tldr,
                            's2_fields_of_study': json.dumps(fields_of_study) if fields_of_study else None,
                            'open_access_pdf_url': open_access_pdf_url,
                            's2_matched_at': datetime.now().isoformat(),
                        }
                        db.update_paper_metadata(request.doi, metadata_update)

                        # Build citation relationships
                        if s2_paper_id:
                            # Get papers with s2_id for internal citation check
                            existing_papers = db.get_papers_with_s2_id()
                            s2_to_doi = {p['s2_paper_id']: p['doi'] for p in existing_papers if p.get('s2_paper_id')}

                            # Get references (papers this paper cites)
                            try:
                                references = s2_client.get_paper_references(s2_paper_id, limit=50)
                                for ref in references:
                                    ref_s2_id = ref.get('paperId')
                                    if not ref_s2_id:
                                        continue

                                    is_internal = ref_s2_id in s2_to_doi
                                    citation_data = {
                                        'citing_paper_id': request.doi,
                                        'cited_paper_id': s2_to_doi.get(ref_s2_id, ref_s2_id),
                                        'citing_s2_id': s2_paper_id,
                                        'cited_s2_id': ref_s2_id,
                                        'citing_title': paper.get('title'),
                                        'citing_year': paper.get('year'),
                                        'cited_title': ref.get('title'),
                                        'cited_year': ref.get('year'),
                                        'cited_citation_count': ref.get('citationCount', 0),
                                        'is_internal': is_internal
                                    }
                                    db.add_paper_citation(citation_data)
                                    citation_count += 1
                            except Exception as e:
                                print(f"Failed to get references for {s2_paper_id}: {e}")

                            # Get citations (papers that cite this paper)
                            try:
                                citations = s2_client.get_paper_citations(s2_paper_id, limit=50)
                                for cit in citations:
                                    cit_s2_id = cit.get('paperId')
                                    if not cit_s2_id:
                                        continue

                                    is_internal = cit_s2_id in s2_to_doi
                                    citation_data = {
                                        'citing_paper_id': s2_to_doi.get(cit_s2_id, cit_s2_id),
                                        'cited_paper_id': request.doi,
                                        'citing_s2_id': cit_s2_id,
                                        'cited_s2_id': s2_paper_id,
                                        'citing_title': cit.get('title'),
                                        'citing_year': cit.get('year'),
                                        'cited_title': paper.get('title'),
                                        'cited_year': paper.get('year'),
                                        'cited_citation_count': s2_data.get('citationCount', 0),
                                        'is_internal': is_internal
                                    }
                                    db.add_paper_citation(citation_data)
                                    citation_count += 1
                            except Exception as e:
                                print(f"Failed to get citations for {s2_paper_id}: {e}")

                except Exception as e:
                    print(f"S2 matching failed for {request.doi}: {e}")

            duration = time.time() - start_time
            concepts_count = count_concepts(concept_tree)

            return {
                "success": True,
                "message": "Paper processed successfully with S2 metadata and citations",
                "concept_tree": concept_tree,
                "duration": duration,
                "concepts_count": concepts_count,
                "s2_matched": s2_data is not None,
                "citations_added": citation_count
            }
        else:
            duration = time.time() - start_time
            return {
                "success": False,
                "message": "Failed to extract concepts",
                "duration": duration,
                "concepts_count": 0
            }

    except Exception as e:
        duration = time.time() - start_time
        raise HTTPException(status_code=500, detail={"error": str(e), "duration": duration})


def count_concepts(tree: dict) -> int:
    """Count total concepts in tree including root"""
    if not tree:
        return 0
    count = 1  # root
    for child in tree.get('children', []):
        count += count_concepts(child)
    return count


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
    """Delete a paper and its orphaned concepts"""
    db = get_db()
    paper = db.get_paper(doi)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # Delete PDF file if exists
    pdf_path = paper.get('pdf_path')
    if pdf_path and Path(pdf_path).exists():
        Path(pdf_path).unlink()

    # Use cascade delete
    db.delete_paper_cascade(doi)

    return {"success": True, "message": "Paper and orphaned concepts deleted"}


class AddFromS2Request(BaseModel):
    """从 S2 添加论文元数据"""
    s2_paper_id: str
    title: str
    year: Optional[int] = None
    abstract: Optional[str] = None
    authors: Optional[List[str]] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = 0
    tldr: Optional[str] = None
    open_access_pdf_url: Optional[str] = None


class DownloadAndProcessRequest(BaseModel):
    """下载 PDF 并处理"""
    s2_paper_id: str
    title: str
    open_access_pdf_url: str
    year: Optional[int] = None
    abstract: Optional[str] = None
    authors: Optional[List[str]] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = 0
    tldr: Optional[str] = None


@router.post("/add-from-s2")
def add_paper_from_s2(request: AddFromS2Request):
    """
    仅添加 S2 元数据，不处理 PDF。

    论文会出现在列表中，但不会有概念树。
    引用关系仍会在引用图谱中显示。
    """
    db = get_db()

    # 检查是否已存在
    existing = db.get_paper_by_s2_id(request.s2_paper_id)
    if existing:
        return {
            "success": False,
            "message": "Paper already exists in graph",
            "doi": existing['doi']
        }

    # 使用 S2 paper ID 作为 DOI（如果没有真实 DOI）
    doi = request.s2_paper_id

    # 创建论文记录
    paper_data = {
        'doi': doi,
        'title': request.title,
        'abstract': request.abstract or "",
        'authors': request.authors or [],
        'year': request.year,
        'venue': request.venue,
        'citation_count': request.citation_count,
        'tldr': request.tldr,
        's2_paper_id': request.s2_paper_id,
        's2_matched_at': datetime.now().isoformat(),
        'open_access_pdf_url': request.open_access_pdf_url,
        'pdf_path': None,  # 没有 PDF
        'status': 'processed',  # 标记为已处理（虽然没有概念树）
    }

    try:
        db.add_paper(paper_data)
        return {
            "success": True,
            "message": "Paper metadata added successfully",
            "doi": doi,
            "title": request.title
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download-and-process")
async def download_and_process_paper(request: DownloadAndProcessRequest):
    """
    下载开放获取 PDF 并自动处理。

    1. 下载 PDF 到 papers/pending/ 目录
    2. 创建论文记录
    3. 自动触发处理流程（PyMuPDF + S2 匹配 + LLM 提取）
    """
    import requests

    db = get_db()
    parser = get_parser()
    extractor = get_extractor()

    if not extractor:
        raise HTTPException(status_code=400, detail="LLM not configured")

    # 检查是否已存在
    existing = db.get_paper_by_s2_id(request.s2_paper_id)
    if existing:
        return {
            "success": False,
            "message": "Paper already exists in graph",
            "doi": existing['doi']
        }

    # 下载 PDF
    project_root = Path(__file__).parent.parent.parent
    pending_dir = project_root / "papers" / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    # 生成安全文件名
    safe_title = request.title[:50].replace('/', '_').replace('\\', '_').replace(':', '_')
    unique_name = f"{safe_title}_{int(time.time())}.pdf"
    file_path = pending_dir / unique_name

    try:
        # 下载 PDF
        response = requests.get(request.open_access_pdf_url, timeout=30)
        response.raise_for_status()
        with open(file_path, "wb") as f:
            f.write(response.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download PDF: {str(e)}")

    # 使用 S2 paper ID 作为 DOI
    doi = request.s2_paper_id

    # 先解析 PDF 提取基本信息
    try:
        content = await asyncio.to_thread(parser.parse, str(file_path))
    except Exception as e:
        print(f"PDF parse error: {e}")
        content = None

    # 创建论文记录（使用 S2 元数据作为基础）
    paper_data = {
        'doi': doi,
        'title': request.title,
        'abstract': request.abstract or (content.abstract if content else "") or "",
        'authors': request.authors or (content.authors if content else []) or [],
        'year': request.year,
        'venue': request.venue,
        'citation_count': request.citation_count,
        'tldr': request.tldr,
        's2_paper_id': request.s2_paper_id,
        's2_matched_at': datetime.now().isoformat(),
        'open_access_pdf_url': request.open_access_pdf_url,
        'pdf_path': str(file_path),
        'status': 'pending',
    }

    try:
        db.add_paper(paper_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create paper: {str(e)}")

    # 自动触发处理流程
    try:
        # 提取概念
        concept_tree = None
        if content and content.full_text:
            concepts_json = await asyncio.to_thread(extractor.extract_concepts, content.full_text)
            if concepts_json:
                concept_tree = json.loads(concepts_json)

                # 添加概念到图谱
                graph = get_graph()
                root_id = graph.add_concept_tree(doi, concept_tree)
                db.update_paper_status(doi, 'processed')

                # 更新贡献信息
                contribution = db.get_paper_contribution(doi)
                if contribution:
                    db.update_paper_metadata(doi, {
                        'concepts_count': contribution.get('node_count', 0),
                        'root_concept': contribution.get('root_concept')
                    })

        # 构建引用关系
        s2_client = get_s2_client()
        if s2_client and request.s2_paper_id:
            try:
                existing_papers = db.get_papers_with_s2_id()
                s2_to_doi = {p['s2_paper_id']: p['doi'] for p in existing_papers if p.get('s2_paper_id')}

                # Get references
                references = s2_client.get_paper_references(request.s2_paper_id, limit=50)
                for ref in references:
                    ref_s2_id = ref.get('paperId')
                    if not ref_s2_id:
                        continue
                    is_internal = ref_s2_id in s2_to_doi
                    citation_data = {
                        'citing_paper_id': doi,
                        'cited_paper_id': s2_to_doi.get(ref_s2_id, ref_s2_id),
                        'citing_s2_id': request.s2_paper_id,
                        'cited_s2_id': ref_s2_id,
                        'citing_title': request.title,
                        'citing_year': request.year,
                        'cited_title': ref.get('title'),
                        'cited_year': ref.get('year'),
                        'cited_citation_count': ref.get('citationCount', 0),
                        'is_internal': is_internal
                    }
                    db.add_paper_citation(citation_data)
            except Exception as e:
                print(f"Failed to build citations: {e}")

        return {
            "success": True,
            "message": "Paper downloaded and processed successfully",
            "doi": doi,
            "title": request.title,
            "concepts_count": len(concept_tree.get('children', [])) if concept_tree else 0
        }

    except Exception as e:
        # 处理失败但论文已创建
        db.update_paper_status(doi, 'failed')
        return {
            "success": False,
            "message": f"Paper created but processing failed: {str(e)}",
            "doi": doi,
            "title": request.title
        }


@router.patch("/{doi:path}/folder")
def move_paper(doi: str, request: MovePaperRequest):
    """Move paper to a different folder"""
    db = get_db()
    paper = db.get_paper(doi)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    folder_id = request.folder_id
    folder = db.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    db.move_paper_to_folder(doi, folder_id)
    return {"success": True, "message": f"Paper moved to {folder['name']}"}


@router.get("/{doi:path}/contribution")
def get_paper_contribution(doi: str):
    """Get paper's concept contribution"""
    db = get_db()
    paper = db.get_paper(doi)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    return db.get_paper_contribution(doi)


@router.get("/{doi:path}", response_model=PaperResponse)
def get_paper(doi: str):
    """Get a single paper by DOI - must be last among GET routes"""
    db = get_db()
    paper = db.get_paper(doi)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    # Ensure list fields are not None
    if paper.get('keywords') is None:
        paper['keywords'] = []
    if paper.get('contributions') is None:
        paper['contributions'] = []
    if paper.get('authors') is None:
        paper['authors'] = []
    if paper.get('s2_fields_of_study') is None:
        paper['s2_fields_of_study'] = []
    return paper