"""
Agent tools — DeepAgents compatible callable functions.

All tools use langgraph.config.get_config() for dependency injection
instead of module-level globals.
"""

from typing import Any

from langgraph.config import get_config

# ============================================================
# Legacy init for backward compatibility (old LangGraph nodes)
# ============================================================

_db = None
_s2_client = None
_pdf_parser = None
_llm = None


def init_tools(db=None, s2_client=None, pdf_parser=None, llm=None):
    """Initialize legacy module-level globals."""
    global _db, _s2_client, _pdf_parser, _llm
    _db = db
    _s2_client = s2_client
    _pdf_parser = pdf_parser
    _llm = llm


# ============================================================
# Dependency injection helpers
# ============================================================

def _get_db():
    """Get database from runtime config (DeepAgents) or fallback to legacy global."""
    try:
        cfg = get_config()
        return cfg["configurable"]["db"]
    except Exception:
        return _db


def _get_s2_client():
    """Get S2 client from runtime config or fallback to legacy global."""
    try:
        cfg = get_config()
        return cfg["configurable"]["s2_client"]
    except Exception:
        return _s2_client


def _get_pdf_parser():
    """Get PDF parser from runtime config or fallback to legacy global."""
    try:
        cfg = get_config()
        return cfg["configurable"]["pdf_parser"]
    except Exception:
        return _pdf_parser


# ============================================================
# Paper tools
# ============================================================

def search_paper(query: str, limit: int = 10) -> dict[str, Any]:
    """Search for papers in the local database."""
    db = _get_db()
    if not db:
        return {"error": "数据库未初始化"}

    papers = db.get_papers_by_status('processed')
    papers.extend(db.get_papers_by_status('pending'))

    query_lower = query.lower()
    matched = []

    for paper in papers:
        title = (paper.get('title') or '').lower()
        abstract = (paper.get('abstract') or '').lower()
        authors = (paper.get('authors') or '')
        if isinstance(authors, list):
            authors = ' '.join(authors)
        authors = authors.lower()

        score = 0
        if query_lower in title:
            score += 10
        if query_lower in abstract:
            score += 5
        if query_lower in authors:
            score += 3

        if score > 0:
            matched.append((score, paper))

    matched.sort(key=lambda x: x[0], reverse=True)
    result_papers = [p for _, p in matched[:limit]]
    return {"papers": result_papers, "count": len(result_papers)}


def get_paper_by_title(title: str) -> dict[str, Any]:
    """Find a paper by partial title match."""
    db = _get_db()
    if not db:
        return {"error": "数据库未初始化"}

    papers = db.get_papers_by_status('processed')
    papers.extend(db.get_papers_by_status('pending'))

    for paper in papers:
        if title.lower() in (paper.get('title') or '').lower():
            return paper

    return {"error": f"未找到标题包含「{title}」的论文"}


def read_paper_content(title: str, max_chars: int = 10000) -> str:
    """Read full text from a paper's PDF."""
    db = _get_db()
    if not db:
        return "错误：数据库未初始化"

    papers = db.get_papers_by_status('processed')
    papers.extend(db.get_papers_by_status('pending'))

    paper = None
    for p in papers:
        if title.lower() in (p.get('title') or '').lower():
            paper = p
            break

    if not paper:
        return f"错误：未找到论文「{title}」"

    pdf_path = paper.get('pdf_path')
    if not pdf_path:
        return "错误：论文没有关联的 PDF 文件"

    pdf_parser = _get_pdf_parser()
    if not pdf_parser:
        from mkg.pdf_parser import PDFParser
        pdf_parser = PDFParser()

    try:
        text = pdf_parser.extract_text(pdf_path)
        if len(text) > max_chars:
            text = text[:max_chars] + "...(内容过长，已截断)"
        return text
    except Exception as e:
        return f"错误：读取 PDF 失败 - {str(e)}"


# ============================================================
# Citation tools
# ============================================================

def analyze_citations(paper_title: str) -> dict[str, Any]:
    """Analyze citation relationships for a paper."""
    db = _get_db()
    s2_client = _get_s2_client()
    if not db:
        return {"error": "数据库未初始化"}

    papers = db.get_papers_by_status('processed')
    papers.extend(db.get_papers_by_status('pending'))
    paper = None
    for p in papers:
        if paper_title.lower() in (p.get('title') or '').lower():
            paper = p
            break

    if not paper:
        return {"error": f"未找到论文「{paper_title}」"}

    raw_citations = []
    try:
        raw_citations = db.citations.get_paper_citations(paper['doi']) or []
    except Exception:
        pass

    def normalize_db_citation(item: dict) -> dict:
        return {
            "title": item.get("cited_title", ""),
            "year": item.get("cited_year"),
            "citation_count": item.get("cited_citation_count"),
            "paper_id": item.get("cited_s2_id") or item.get("cited_paper_id"),
            "is_internal": bool(item.get("is_internal", 0)),
        }

    def normalize_s2_citation(item: dict) -> dict:
        authors = item.get("authors", [])
        author_names = ", ".join([a.get("name", "") for a in authors[:3]]) if authors else ""
        return {
            "title": item.get("title", ""),
            "year": item.get("year"),
            "citation_count": item.get("citationCount"),
            "paper_id": item.get("paperId"),
            "is_internal": False,
            "authors": author_names,
        }

    citations = [normalize_db_citation(c) for c in raw_citations]

    if not citations and s2_client:
        s2_id = paper.get('s2_paper_id')
        full_title = paper.get('title', '')

        if not s2_id and paper.get('doi'):
            try:
                matched = s2_client.match_paper(title=full_title, doi=paper['doi'])
                if matched:
                    s2_id = matched.get('paperId')
            except Exception:
                pass

        if not s2_id and full_title:
            try:
                results = s2_client.search_papers(full_title, limit=1)
                if results:
                    s2_id = results[0].get('paperId')
            except Exception:
                pass

        if s2_id:
            try:
                s2_data = s2_client.get_paper_citations(s2_id)
                if isinstance(s2_data, list):
                    s2_items = [normalize_s2_citation(c) for c in s2_data[:50]]
                    citations.extend(s2_items)
                elif isinstance(s2_data, dict):
                    s2_items = [normalize_s2_citation(c) for c in s2_data.get('citations', [])[:50]]
                    citations.extend(s2_items)
            except Exception:
                pass

    return {
        "paper": {
            "title": paper.get('title'),
            "doi": paper.get('doi'),
            "citation_count": paper.get('citation_count', len(citations))
        },
        "citations": citations[:20],
        "citation_count": len(citations)
    }


# ============================================================
# Concept tools
# ============================================================

def get_concept_graph(concept_name: str = None) -> dict[str, Any]:
    """Get concept graph data for visualization."""
    db = _get_db()
    if not db:
        return {"error": "数据库未初始化"}

    concept = None
    if concept_name:
        concept = db.get_concept_by_text(concept_name)
        if not concept:
            all_concepts = db.get_all_concepts()
            for c in all_concepts:
                if concept_name.lower() in (c.get('text') or '').lower():
                    concept = c
                    break

    if not concept:
        root_concepts = db.get_root_concepts()
        if root_concepts:
            concept = root_concepts[0]
        else:
            return {"error": "没有可用的概念"}

    concept_id = concept['id']
    children = db.get_concept_children(concept_id) or []
    parents = db.get_concept_parents(concept_id) or []

    return {
        "id": concept_id,
        "name": concept.get('text', ''),
        "category": concept.get('category'),
        "paper_count": concept.get('paper_count', 0),
        "children": [
            {"id": c['id'], "name": c.get('text', ''), "paper_count": c.get('paper_count', 0)}
            for c in children[:10]
        ],
        "parents": [
            {"id": p['id'], "name": p.get('text', ''), "paper_count": p.get('paper_count', 0)}
            for p in parents[:5]
        ],
    }


def analyze_research_points(concept_name: str) -> dict[str, Any]:
    """Analyze research points and directions for a concept."""
    db = _get_db()
    s2_client = _get_s2_client()
    if not db:
        return {"error": "数据库未初始化"}

    concept = db.get_concept_by_text(concept_name)

    if not concept:
        all_concepts = db.get_all_concepts()
        keywords = []
        for n in [4, 3, 2]:
            for i in range(len(concept_name) - n + 1):
                word = concept_name[i:i+n]
                if all('一' <= c <= '鿿' or c.isalpha() for c in word):
                    if word not in ['研究', '分析', '方向', '查看', '帮我', '进行', '的']:
                        keywords.append(word)

        best_match = None
        best_score = 0

        for c in all_concepts:
            text = c.get('text') or ''
            score = 0
            for kw in keywords:
                if kw.lower() in text.lower():
                    score += len(kw)
            if score > best_score:
                best_score = score
                best_match = c

        if best_match and best_score >= 4:
            concept = best_match

    if not concept:
        return {"error": f"未找到概念「{concept_name}」"}

    concept_id = concept['id']
    from backend.services.research_service import ResearchService
    service = ResearchService(db=db, s2_client=s2_client)
    return service.discover_research_points(concept_id)


# ============================================================
# Recommendation tools
# ============================================================

def recommend_papers(concept_name: str, limit: int = 10) -> dict[str, Any]:
    """Recommend papers related to a concept."""
    db = _get_db()
    s2_client = _get_s2_client()
    if not db:
        return {"error": "数据库未初始化"}

    concept = db.get_concept_by_text(concept_name)
    if not concept:
        all_concepts = db.get_all_concepts()
        for c in all_concepts:
            if concept_name.lower() in (c.get('text') or '').lower():
                concept = c
                break

    if concept and not concept.get('text_en'):
        from backend.services.concept_translation import translate_concept_if_needed
        en_name = translate_concept_if_needed(concept, db)
        if en_name and en_name != concept.get('text', ''):
            concept["text_en"] = en_name

    search_query = (concept.get('text_en') or concept_name) if concept else concept_name

    papers = []
    if s2_client:
        try:
            results = s2_client.search_papers(search_query, limit=limit)
            if isinstance(results, list):
                papers = results
            elif isinstance(results, dict):
                papers = results.get('data', results.get('papers', []))
        except Exception as e:
            return {"error": f"搜索失败: {str(e)}"}
    else:
        return {"error": "Semantic Scholar 客户端未初始化，无法推荐论文"}

    return {
        "concept_name": concept.get('text', concept_name) if concept else concept_name,
        "papers": [
            {
                "title": p.get("title", ""),
                "authors": [a.get("name", a) if isinstance(a, dict) else str(a) for a in (p.get("authors") or [])[:5]],
                "year": p.get("year"),
                "abstract": p.get("abstract", ""),
                "citation_count": p.get("citationCount") or p.get("citation_count", 0),
                "venue": p.get("venue", ""),
                "paper_id": p.get("paperId") or p.get("paper_id", ""),
                "open_access_url": (p.get("openAccessPdf") or {}).get("url") if isinstance(p.get("openAccessPdf"), dict) else None,
                "tldr": p.get("tldr", {}).get("text") if isinstance(p.get("tldr"), dict) else p.get("tldr"),
            }
            for p in papers[:limit]
        ],
        "count": len(papers),
    }


# ============================================================
# All tools export
# ============================================================

ALL_TOOLS = [
    search_paper,
    get_paper_by_title,
    read_paper_content,
    analyze_citations,
    get_concept_graph,
    analyze_research_points,
    recommend_papers,
]
