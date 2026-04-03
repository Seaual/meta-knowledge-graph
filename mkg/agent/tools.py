# mkg/agent/tools.py
"""
LangChain Tools - Agent 可调用的工具
"""

from langchain_core.tools import tool
from typing import Optional, List, Dict, Any


# ============================================================
# 依赖注入 - 在运行时初始化
# ============================================================

_db = None
_s2_client = None
_pdf_parser = None


def init_tools(db=None, s2_client=None, pdf_parser=None):
    """
    初始化 Tools 的依赖

    Args:
        db: Database 实例
        s2_client: Semantic Scholar 客户端
        pdf_parser: PDF 解析器
    """
    global _db, _s2_client, _pdf_parser
    _db = db
    _s2_client = s2_client
    _pdf_parser = pdf_parser


# ============================================================
# 论文相关 Tools
# ============================================================

@tool
def search_paper(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    在本地数据库搜索论文

    Args:
        query: 搜索关键词（标题、作者、摘要）
        limit: 返回数量限制

    Returns:
        包含论文列表和数量的字典
    """
    if not _db:
        return {"error": "数据库未初始化"}

    papers = _db.search_papers(query, limit=limit)
    return {"papers": papers, "count": len(papers)}


@tool
def get_paper_by_doi(doi: str) -> Dict[str, Any]:
    """
    根据 DOI 获取论文详情

    Args:
        doi: 论文 DOI

    Returns:
        论文元数据（标题、作者、摘要、关键词等）
    """
    if not _db:
        return {"error": "数据库未初始化"}

    paper = _db.get_paper(doi)
    if not paper:
        return {"error": f"未找到论文: {doi}"}

    return paper


@tool
def get_paper_by_title(title: str) -> Dict[str, Any]:
    """
    根据标题模糊匹配论文

    Args:
        title: 论文标题（支持部分匹配）

    Returns:
        匹配的论文信息
    """
    if not _db:
        return {"error": "数据库未初始化"}

    # 获取所有已处理论文
    papers = _db.get_papers_by_status('processed')
    papers.extend(_db.get_papers_by_status('pending'))

    # 模糊匹配
    for paper in papers:
        if title.lower() in (paper.get('title') or '').lower():
            return paper

    return {"error": f"未找到标题包含「{title}」的论文"}


@tool
def get_paper_citations(doi: str, include_s2: bool = True) -> Dict[str, Any]:
    """
    获取论文的引用关系

    Args:
        doi: 论文 DOI
        include_s2: 是否从 Semantic Scholar 补充数据

    Returns:
        包含论文信息和引用列表的字典
    """
    if not _db:
        return {"error": "数据库未初始化"}

    paper = _db.get_paper(doi)
    if not paper:
        return {"error": f"未找到论文: {doi}"}

    # 获取本地引用数据
    citations = _db.get_citations(doi) if hasattr(_db, 'get_citations') else []

    # 从 S2 补充
    if include_s2 and _s2_client and paper.get('s2_paper_id'):
        try:
            s2_data = _s2_client.get_paper_citations(paper['s2_paper_id'])
            if s2_data:
                citations.extend(s2_data.get('citations', []))
        except Exception as e:
            print(f"S2 API error: {e}")

    return {
        "paper": paper,
        "citations": citations,
        "citation_count": len(citations)
    }


# ============================================================
# 概念相关 Tools
# ============================================================

@tool
def get_concept_papers(concept_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    获取概念关联的论文列表

    Args:
        concept_id: 概念 ID
        limit: 返回数量限制

    Returns:
        论文列表
    """
    if not _db:
        return []

    papers = _db.get_concept_papers(concept_id, limit=limit)
    return papers


@tool
def get_concept_info(concept_id: str) -> Dict[str, Any]:
    """
    获取概念详情

    Args:
        concept_id: 概念 ID

    Returns:
        概念信息（文本、层级、关联论文数）
    """
    if not _db:
        return {"error": "数据库未初始化"}

    concept = _db.get_concept(concept_id)
    if not concept:
        return {"error": f"未找到概念: {concept_id}"}

    return concept


# ============================================================
# Semantic Scholar Tools
# ============================================================

@tool
def search_s2_papers(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    在 Semantic Scholar 搜索论文（外部数据源）

    Args:
        query: 搜索查询
        limit: 返回数量限制

    Returns:
        论文列表（包含标题、摘要、引用数等）
    """
    if not _s2_client:
        return [{"error": "Semantic Scholar 客户端未初始化"}]

    try:
        results = _s2_client.search_paper(query, limit=limit)
        return results
    except Exception as e:
        return [{"error": f"搜索失败: {str(e)}"}]


# ============================================================
# PDF 相关 Tools
# ============================================================

@tool
def read_pdf_content(doi: str, max_chars: int = 10000) -> str:
    """
    读取论文 PDF 全文

    Args:
        doi: 论文 DOI
        max_chars: 最大字符数，超出则截断

    Returns:
        论文全文文本
    """
    if not _db:
        return "错误：数据库未初始化"

    paper = _db.get_paper(doi)
    if not paper:
        return f"错误：未找到论文 {doi}"

    pdf_path = paper.get('pdf_path')
    if not pdf_path:
        return "错误：论文没有关联的 PDF 文件"

    # 懒加载 PDF Parser
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
# 文件夹管理 Tools
# ============================================================

@tool
def list_folders() -> List[Dict[str, Any]]:
    """
    获取所有文件夹列表

    Returns:
        文件夹列表（包含 ID、名称、论文数）
    """
    if not _db:
        return []

    folders = _db.get_all_folders()
    return folders


@tool
def move_paper_to_folder(doi: str, folder_name: str, create_if_not_exist: bool = False) -> str:
    """
    移动论文到指定文件夹

    Args:
        doi: 论文 DOI
        folder_name: 目标文件夹名称
        create_if_not_exist: 文件夹不存在时是否创建

    Returns:
        操作结果消息
    """
    if not _db:
        return "错误：数据库未初始化"

    # 查找论文
    paper = _db.get_paper(doi)
    if not paper:
        return f"错误：未找到论文 {doi}"

    # 查找文件夹
    folders = _db.get_all_folders()
    target = next((f for f in folders if f['name'] == folder_name), None)

    if not target and create_if_not_exist:
        folder_id = _db.create_folder({'name': folder_name})
        target = {'id': folder_id, 'name': folder_name}
    elif not target:
        return f"错误：文件夹「{folder_name}」不存在。需要我创建吗？"

    # 移动论文
    _db.move_paper_to_folder(doi, target['id'])
    return f"已将论文《{paper.get('title', doi)}》移动到文件夹「{folder_name}」"


@tool
def create_folder(name: str, description: str = "") -> str:
    """
    创建新文件夹

    Args:
        name: 文件夹名称
        description: 文件夹描述

    Returns:
        操作结果消息
    """
    if not _db:
        return "错误：数据库未初始化"

    folder_id = _db.create_folder({'name': name, 'description': description})
    return f"已创建文件夹「{name}」(ID: {folder_id})"


# ============================================================
# 工具集合
# ============================================================

# Lead Node 可用的工具
LEAD_TOOLS = [search_paper, list_folders, move_paper_to_folder, create_folder]

# Citation Node 可用的工具
CITATION_TOOLS = [get_paper_by_doi, get_paper_by_title, get_paper_citations, search_s2_papers]

# Research Node 可用的工具
RESEARCH_TOOLS = [get_concept_info, get_concept_papers, search_s2_papers]

# Paper QA Node 可用的工具
PAPER_QA_TOOLS = [get_paper_by_doi, get_paper_by_title, read_pdf_content]

# Deep Research Node 可用的工具（全部）
DEEP_RESEARCH_TOOLS = [
    search_paper, get_paper_by_doi, get_paper_by_title,
    get_paper_citations, get_concept_info, get_concept_papers,
    search_s2_papers, read_pdf_content
]