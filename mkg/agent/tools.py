# mkg/agent/tools.py
"""
LangChain Tools - Agent 可调用的工具

所有功能都作为 tool，由 lead agent 统一调用
"""

from langchain_core.tools import tool
from typing import Optional, List, Dict, Any

from mkg.llm import get_llm_or_raise, generate


# ============================================================
# 依赖注入 - 在运行时初始化
# ============================================================

_db = None
_s2_client = None
_pdf_parser = None
_llm = None


def init_tools(db=None, s2_client=None, pdf_parser=None, llm=None):
    """
    初始化 Tools 的依赖

    Args:
        db: Database 实例
        s2_client: Semantic Scholar 客户端
        pdf_parser: PDF 解析器
        llm: LLM 客户端
    """
    global _db, _s2_client, _pdf_parser, _llm
    _db = db
    _s2_client = s2_client
    _pdf_parser = pdf_parser
    _llm = llm


# ============================================================
# 论文相关 Tools
# ============================================================

@tool
def search_paper(query: str, limit: int = 10) -> Dict[str, Any]:
    """搜索论文。当用户问「有哪些论文」「搜索论文」「找论文」「XX下有什么论文」时使用。

    在本地数据库中搜索论文，支持按标题、作者、摘要、概念名搜索。
    返回论文列表，包含标题、作者、摘要等信息。

    Args:
        query: 搜索关键词（可以是概念名如"多智能体"、论文标题、作者名等）
        limit: 返回数量限制，默认10

    Returns:
        包含论文列表和数量的字典，如 {"papers": [...], "count": 5}
    """
    if not _db:
        return {"error": "数据库未初始化"}

    # 获取所有已处理论文
    papers = _db.get_papers_by_status('processed')
    papers.extend(_db.get_papers_by_status('pending'))

    # 本地搜索：匹配标题、摘要、作者
    query_lower = query.lower()
    matched = []

    for paper in papers:
        title = (paper.get('title') or '').lower()
        abstract = (paper.get('abstract') or '').lower()
        authors = (paper.get('authors') or '')
        if isinstance(authors, list):
            authors = ' '.join(authors)
        authors = authors.lower()

        # 计算匹配分数
        score = 0
        if query_lower in title:
            score += 10
        if query_lower in abstract:
            score += 5
        if query_lower in authors:
            score += 3

        if score > 0:
            matched.append((score, paper))

    # 按分数排序
    matched.sort(key=lambda x: x[0], reverse=True)

    # 返回结果
    result_papers = [p for _, p in matched[:limit]]
    return {"papers": result_papers, "count": len(result_papers)}


@tool
def get_paper_by_title(title: str) -> Dict[str, Any]:
    """根据标题查找论文。

    支持部分匹配，返回最匹配的论文信息。

    Args:
        title: 论文标题（可以是部分标题）

    Returns:
        论文详情，包含标题、作者、摘要、DOI等
    """
    if not _db:
        return {"error": "数据库未初始化"}

    papers = _db.get_papers_by_status('processed')
    papers.extend(_db.get_papers_by_status('pending'))

    for paper in papers:
        if title.lower() in (paper.get('title') or '').lower():
            return paper

    return {"error": f"未找到标题包含「{title}」的论文"}


@tool
def read_paper_content(title: str, max_chars: int = 10000) -> str:
    """读取论文 PDF 内容。

    用于回答关于论文内容的问题。返回论文全文文本。

    Args:
        title: 论文标题
        max_chars: 最大字符数

    Returns:
        论文全文文本
    """
    if not _db:
        return "错误：数据库未初始化"

    # 查找论文
    papers = _db.get_papers_by_status('processed')
    papers.extend(_db.get_papers_by_status('pending'))

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

    global _pdf_parser
    if not _pdf_parser:
        from mkg.pdf_parser import PDFParser
        _pdf_parser = PDFParser()

    try:
        text = _pdf_parser.extract_text(pdf_path)
        if len(text) > max_chars:
            text = text[:max_chars] + "...(内容过长，已截断)"
        return text
    except Exception as e:
        return f"错误：读取 PDF 失败 - {str(e)}"


# ============================================================
# 引用分析 Tools
# ============================================================

@tool
def analyze_citations(paper_title: str) -> Dict[str, Any]:
    """分析论文的引用关系。

    当用户问"引用关系"、"被谁引用"、"引用了谁"时调用。
    返回论文的引用和被引用列表。

    Args:
        paper_title: 论文标题

    Returns:
        引用分析结果，包含引用列表和被引用列表
    """
    if not _db:
        return {"error": "数据库未初始化"}

    # 查找论文
    papers = _db.get_papers_by_status('processed')
    paper = None
    for p in papers:
        if paper_title.lower() in (p.get('title') or '').lower():
            paper = p
            break

    if not paper:
        return {"error": f"未找到论文「{paper_title}」"}

    # 获取引用数据
    citations = []
    if hasattr(_db, 'get_citations'):
        citations = _db.get_citations(paper['doi']) or []

    # 从 S2 补充
    if _s2_client and paper.get('s2_paper_id'):
        try:
            s2_data = _s2_client.get_paper_citations(paper['s2_paper_id'])
            if s2_data:
                citations.extend(s2_data.get('citations', []))
        except Exception as e:
            print(f"S2 API error: {e}")

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
# 概念相关 Tools
# ============================================================

@tool
def get_concept_graph(concept_name: str = None) -> Dict[str, Any]:
    """显示概念图谱的可视化界面。

    【重要】仅当用户明确说「查看图谱」「显示图谱」「概念图谱」时才调用此工具！

    不要在以下情况使用：
    - 用户问研究点、研究方向 → 用 analyze_research_points
    - 用户问论文 → 用 search_paper

    Args:
        concept_name: 概念名称（可选，不提供则返回根概念）

    Returns:
        概念图谱数据，用于前端渲染图谱组件
    """
    if not _db:
        return {"error": "数据库未初始化"}

    concept = None

    if concept_name:
        concept = _db.get_concept_by_text(concept_name)
        if not concept:
            all_concepts = _db.get_all_concepts()
            for c in all_concepts:
                if concept_name.lower() in (c.get('text') or '').lower():
                    concept = c
                    break

    if not concept:
        root_concepts = _db.get_root_concepts()
        if root_concepts:
            concept = root_concepts[0]
        else:
            return {"error": "没有可用的概念"}

    concept_id = concept['id']
    children = _db.get_concept_children(concept_id) or []
    parents = _db.get_concept_parents(concept_id) or []

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


@tool
def analyze_research_points(concept_name: str) -> Dict[str, Any]:
    """分析概念的研究点和研究方向。

    【重要】当用户提到「研究点」「研究方向」「研究机会」「分析...的研究点」时调用此工具！

    这个工具用于分析某个概念的研究现状和潜在研究方向。
    会调用 LLM 深入分析图谱结构，生成研究点建议。

    不要与 get_concept_graph 混淆：
    - 用户说「研究点」→ 用这个工具 analyze_research_points
    - 用户说「查看图谱」→ 用 get_concept_graph

    Args:
        concept_name: 概念名称

    Returns:
        研究点分析结果，包含 LLM 生成的研究点列表
    """
    print(f"DEBUG analyze_research_points: concept_name={concept_name}")

    if not _db:
        print("DEBUG: 数据库未初始化")
        return {"error": "数据库未初始化"}

    concept = _db.get_concept_by_text(concept_name)
    print(f"DEBUG: 直接匹配结果={concept}")

    if not concept:
        all_concepts = _db.get_all_concepts()
        for c in all_concepts:
            if concept_name.lower() in (c.get('text') or '').lower():
                concept = c
                print(f"DEBUG: 模糊匹配结果={c.get('text')}")
                break

    if not concept:
        print(f"DEBUG: 未找到概念「{concept_name}」")
        return {"error": f"未找到概念「{concept_name}」"}

    concept_id = concept['id']
    print(f"DEBUG: concept_id={concept_id}")

    # 调用与概念页面相同的研究点分析 API
    try:
        import requests
        url = f"http://localhost:8000/api/concepts/{concept_id}/research-points"
        print(f"DEBUG: 调用API={url}")
        res = requests.get(url, timeout=120)
        print(f"DEBUG: API返回状态码={res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print(f"DEBUG: 研究点数量={len(data.get('research_points', []))}")
            return {
                "concept_name": data.get("concept_name", concept.get("text", concept_name)),
                "research_points": data.get("research_points", []),
                "analysis_context": data.get("analysis_context", {}),
            }
        else:
            return {"error": f"研究点分析失败: HTTP {res.status_code}"}
    except Exception as e:
        print(f"DEBUG: 异常={e}")
        # Fallback：返回基础概念数据
        papers = _db.get_papers_by_concept(concept_id) or []
        children = _db.get_concept_children(concept_id) or []
        parents = _db.get_concept_parents(concept_id) or []

        return {
            "concept_name": concept.get('text', concept_name),
            "research_points": [],
            "analysis_context": {
                "concept": {"id": concept_id, "name": concept.get("text"), "category": concept.get("category")},
                "ancestors": [{"id": p["id"], "name": p.get("text")} for p in parents],
                "descendants": [{"id": c["id"], "name": c.get("text")} for c in children],
                "edge_nodes": [],
                "related_papers": [{"title": p.get("title")} for p in papers[:5]],
            },
            "local_papers": papers,
            "children_concepts": [c.get('text') for c in children],
            "parent_concepts": [p.get('text') for p in parents],
        }


# ============================================================
# 文件夹管理 Tools
# ============================================================

@tool
def list_folders() -> List[Dict[str, Any]]:
    """获取所有文件夹列表。

    Returns:
        文件夹列表
    """
    if not _db:
        return []
    return _db.get_all_folders()


@tool
def move_paper_to_folder(paper_title: str, folder_name: str) -> str:
    """移动论文到指定文件夹。

    当用户说"移动到"、"放到"某文件夹时调用。

    Args:
        paper_title: 论文标题
        folder_name: 目标文件夹名称

    Returns:
        操作结果
    """
    if not _db:
        return "错误：数据库未初始化"

    # 查找论文
    papers = _db.get_papers_by_status('processed')
    papers.extend(_db.get_papers_by_status('pending'))

    paper = None
    for p in papers:
        if paper_title.lower() in (p.get('title') or '').lower():
            paper = p
            break

    if not paper:
        return f"错误：未找到论文「{paper_title}」"

    # 查找或创建文件夹
    folders = _db.get_all_folders()
    target = next((f for f in folders if f['name'] == folder_name), None)

    if not target:
        folder_id = _db.create_folder({'name': folder_name})
        target = {'id': folder_id, 'name': folder_name}

    _db.move_paper_to_folder(paper['doi'], target['id'])
    return f"已将论文《{paper.get('title')}》移动到文件夹「{folder_name}」"


@tool
def create_folder(name: str, description: str = "") -> str:
    """创建新文件夹。

    Args:
        name: 文件夹名称
        description: 文件夹描述

    Returns:
        操作结果
    """
    if not _db:
        return "错误：数据库未初始化"

    folder_id = _db.create_folder({'name': name, 'description': description})
    return f"已创建文件夹「{name}」"


# ============================================================
# 论文推荐 Tools
# ============================================================

@tool
def recommend_papers(concept_name: str, limit: int = 10) -> Dict[str, Any]:
    """推荐与某概念相关的论文。

    当用户说「推荐论文」「相关论文」「找相关工作」「有什么新论文」时调用。

    Args:
        concept_name: 概念名称
        limit: 返回数量限制，默认10

    Returns:
        推荐论文列表，包含标题、作者、摘要等
    """
    if not _db:
        return {"error": "数据库未初始化"}

    # 查找概念（获取英文名用于搜索）
    concept = _db.get_concept_by_text(concept_name)
    if not concept:
        all_concepts = _db.get_all_concepts()
        for c in all_concepts:
            if concept_name.lower() in (c.get('text') or '').lower():
                concept = c
                break

    # 使用英文名搜索（如果有），否则用中文名
    search_query = concept_name
    if concept and concept.get('text_en'):
        search_query = concept['text_en']
    elif concept:
        search_query = concept.get('text', concept_name)

    papers = []
    if _s2_client:
        try:
            results = _s2_client.search_papers(search_query, limit=limit)
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
# Deep Research Tool
# ============================================================

@tool
def deep_research(target_name: str, target_type: str, query: str,
                  dimensions: Optional[List[str]] = None) -> Dict[str, Any]:
    """深入研究 - 多智能体协作分析。

    启动多个维度的研究 agent，并行分析后综合报告。
    当用户说"深入研究"、"全面分析"时调用。

    Args:
        target_name: 研究目标名称（概念或论文标题）
        target_type: 目标类型 ('concept' | 'paper')
        query: 研究问题
        dimensions: 研究维度（可选，默认自动生成）

    Returns:
        研究报告，包含各维度分析和综合结论
    """
    from mkg.agent.research_graph import run_deep_research

    try:
        result = run_deep_research(
            target_name=target_name,
            target_type=target_type,
            query=query,
            dimensions=dimensions
        )
        return result
    except Exception as e:
        return {"error": f"深入研究失败: {str(e)}"}


# ============================================================
# 所有工具集合
# ============================================================

ALL_TOOLS = [
    # 论文相关
    search_paper,
    get_paper_by_title,
    read_paper_content,
    # 引用分析
    analyze_citations,
    # 概念相关
    get_concept_graph,
    analyze_research_points,
    # 论文推荐
    recommend_papers,
    # 深入研究
    deep_research,
    # 文件夹管理
    list_folders,
    move_paper_to_folder,
    create_folder,
]