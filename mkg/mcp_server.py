# mkg/mcp_server.py
"""
MCP Server for Meta Knowledge Graph tools.

使用 FastMCP 创建 MCP server，暴露所有工具。
"""

from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, Optional
import os

# 初始化 FastMCP
mcp = FastMCP("mkg-tools")

# 数据库连接（延迟初始化）
_db = None


def _get_db():
    """获取数据库连接"""
    global _db
    if _db is None:
        from mkg.database import Database
        db_path = os.environ.get("MKG_DB_PATH", "data/mkg.db")
        _db = Database(db_path)
        _db.connect()
    return _db


# ============================================================
# 论文相关工具
# ============================================================

@mcp.tool()
def search_paper(query: str, limit: int = 10) -> Dict[str, Any]:
    """搜索论文。

    当用户问「有哪些论文」「搜索论文」「找论文」「XX概念下的论文」时使用此工具。
    返回匹配的论文列表，包含标题、作者、摘要等信息。

    Args:
        query: 搜索关键词（概念名、论文标题、作者名等）
        limit: 返回数量限制，默认10

    Returns:
        {"papers": [...], "count": N}
    """
    db = _get_db()

    # 获取所有已处理论文
    papers = db.get_papers_by_status('processed')
    papers.extend(db.get_papers_by_status('pending'))

    # 简单的本地搜索：匹配标题、摘要、作者
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


@mcp.tool()
def get_paper_by_title(title: str) -> Dict[str, Any]:
    """根据标题查找论文详情。

    Args:
        title: 论文标题（可以是部分标题）

    Returns:
        论文详情，包含标题、作者、摘要、DOI等
    """
    db = _get_db()
    papers = db.get_papers_by_status('processed')
    papers.extend(db.get_papers_by_status('pending'))

    for paper in papers:
        if title.lower() in (paper.get('title') or '').lower():
            return paper

    return {"error": f"未找到标题包含「{title}」的论文"}


@mcp.tool()
def read_paper_content(title: str, max_chars: int = 10000) -> str:
    """读取论文 PDF 内容。

    用于回答关于论文内容的问题。

    Args:
        title: 论文标题
        max_chars: 最大字符数，默认10000

    Returns:
        论文全文文本
    """
    db = _get_db()
    papers = db.get_papers_by_status('processed')

    for paper in papers:
        if title.lower() in (paper.get('title') or '').lower():
            content_path = paper.get('content_path')
            if content_path and os.path.exists(content_path):
                with open(content_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    return content[:max_chars] if len(content) > max_chars else content
            return f"论文「{paper.get('title')}」的内容文件不存在"

    return f"未找到论文「{title}」"


@mcp.tool()
def analyze_citations(doi: str) -> Dict[str, Any]:
    """分析论文的引用关系。

    当用户问「引用」「被引用」「引用了哪些论文」时使用。

    Args:
        doi: 论文 DOI

    Returns:
        {"cited_by": [...], "references": [...]}
    """
    db = _get_db()
    paper = db.get_paper(doi)

    if not paper:
        return {"error": f"未找到 DOI 为 {doi} 的论文"}

    # 获取引用关系
    references = db.get_paper_citations(doi) or []  # 这篇论文引用了谁
    cited_by = db.get_paper_cited_by(doi) or []  # 谁引用了这篇论文

    return {
        "paper": paper.get('title', ''),
        "cited_by": [{"doi": p.get('cited_paper_doi'), "title": p.get('cited_paper_title')} for p in cited_by[:10]],
        "references": [{"doi": r.get('cited_paper_doi'), "title": r.get('cited_paper_title')} for r in references[:10]],
        "cited_by_count": len(cited_by),
        "references_count": len(references),
    }


# ============================================================
# 概念相关工具
# ============================================================

@mcp.tool()
def get_concept_graph(concept_name: Optional[str] = None) -> Dict[str, Any]:
    """显示概念图谱可视化。

    仅当用户明确要求「查看图谱」「显示图谱」「概念图谱」时调用此工具。
    用于可视化展示概念之间的层级关系。

    注意：如果用户问论文列表、搜索论文，请使用 search_paper，不要使用此工具！

    Args:
        concept_name: 概念名称（可选，不提供则返回根概念）

    Returns:
        图谱数据，包含节点和关系，用于前端渲染
    """
    db = _get_db()
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


@mcp.tool()
def analyze_research_points(concept_name: str) -> Dict[str, Any]:
    """分析概念的研究点。

    当用户问「研究点」「研究方向」「XX概念的研究点」时使用。

    Args:
        concept_name: 概念名称

    Returns:
        {"concept": "...", "research_points": [...]}
    """
    db = _get_db()
    concept = db.get_concept_by_text(concept_name)

    if not concept:
        all_concepts = db.get_all_concepts()
        for c in all_concepts:
            if concept_name.lower() in (c.get('text') or '').lower():
                concept = c
                break

    if not concept:
        return {"error": f"未找到概念「{concept_name}」"}

    # 获取相关论文 - 使用本地搜索
    all_papers = db.get_papers_by_status('processed')
    all_papers.extend(db.get_papers_by_status('pending'))

    concept_text = concept.get('text', '').lower()
    related_papers = []
    for paper in all_papers:
        title = (paper.get('title') or '').lower()
        abstract = (paper.get('abstract') or '').lower()
        if concept_text in title or concept_text in abstract:
            related_papers.append(paper)
            if len(related_papers) >= 10:
                break

    return {
        "concept": concept.get('text', ''),
        "category": concept.get('category'),
        "paper_count": concept.get('paper_count', 0),
        "related_papers": [
            {"title": p.get('title'), "doi": p.get('doi')}
            for p in related_papers[:10]
        ],
        "children": db.get_concept_children(concept['id']),
    }


# ============================================================
# 文件夹管理工具
# ============================================================

@mcp.tool()
def list_folders() -> Dict[str, Any]:
    """列出所有文件夹。

    Returns:
        {"folders": [...]}
    """
    db = _get_db()
    folders = db.get_all_folders()
    return {"folders": folders}


@mcp.tool()
def create_folder(name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
    """创建新文件夹。

    Args:
        name: 文件夹名称
        parent_id: 父文件夹ID（可选）

    Returns:
        {"success": true, "folder_id": "..."}
    """
    db = _get_db()
    folder_id = db.create_folder({"name": name})
    return {"success": True, "folder_id": folder_id}


@mcp.tool()
def move_paper_to_folder(doi: str, folder_id: str) -> Dict[str, Any]:
    """移动论文到文件夹。

    Args:
        doi: 论文 DOI
        folder_id: 目标文件夹ID

    Returns:
        {"success": true}
    """
    db = _get_db()
    db.move_paper_to_folder(doi, folder_id)
    return {"success": True}


# ============================================================
# 深入研究工具
# ============================================================

@mcp.tool()
def deep_research(
    target_name: str,
    target_type: str = "concept",
    query: str = "",
    dimensions: list = None
) -> Dict[str, Any]:
    """深入研究某个主题。

    使用多智能体协作进行深入研究，返回研究报告。

    Args:
        target_name: 目标名称（概念名或论文标题）
        target_type: 目标类型，"concept" 或 "paper"
        query: 具体问题（可选）
        dimensions: 研究维度列表，如 ["技术分析", "应用场景"]

    Returns:
        {"report": "...", "dimensions": [...]}
    """
    from mkg.agent.research_graph import run_deep_research
    from mkg.llm import init_llm_from_db

    # 初始化 LLM
    init_llm_from_db(_get_db())

    if dimensions is None:
        dimensions = ["技术分析", "应用场景", "发展趋势", "挑战与机遇"]

    result = run_deep_research(
        target_name=target_name,
        target_type=target_type,
        query=query,
        dimensions=dimensions
    )

    return result


def run_server():
    """运行 MCP server"""
    mcp.run()


if __name__ == "__main__":
    run_server()