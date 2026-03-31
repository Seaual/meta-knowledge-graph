"""
引用网络构建模块

为图谱中所有已匹配 S2 的论文，拉取引用关系并存储。
"""

import json
import logging
from typing import List, Dict, Optional
from tqdm import tqdm

logger = logging.getLogger("mkg.citation_graph")


def build_citation_graph(db, s2_client, progress_callback=None):
    """
    为所有已匹配 S2 的论文拉取引用关系

    Args:
        db: Database 实例
        s2_client: S2Client 实例
        progress_callback: 进度回调函数 (current, total, message)

    Returns:
        {
            'total_papers': 总论文数,
            'processed': 处理数,
            'total_citations': 总引用关系数,
            'internal_edges': 内部边数,
            'errors': 错误列表
        }
    """
    # 获取所有有 S2 paper ID 的论文
    papers = db.get_papers_with_s2_id()

    if not papers:
        return {
            'total_papers': 0,
            'processed': 0,
            'total_citations': 0,
            'internal_edges': 0,
            'errors': []
        }

    total = len(papers)
    processed = 0
    total_citations = 0
    internal_edges = 0
    errors = []

    # 构建 S2 paper ID 到本地 DOI 的映射
    s2_to_doi = {p['s2_paper_id']: p['doi'] for p in papers if p.get('s2_paper_id')}

    # 清除旧数据
    db.clear_paper_citations()

    for i, paper in enumerate(papers):
        paper_doi = paper['doi']
        s2_id = paper['s2_paper_id']

        if progress_callback:
            progress_callback(i + 1, total, f"Processing: {paper['title'][:50]}...")

        try:
            # 获取这篇论文引用了谁（参考文献）
            references = s2_client.get_paper_references(s2_id, limit=200)

            for ref in references:
                ref_s2_id = ref.get('paperId')
                ref_title = ref.get('title')
                ref_year = ref.get('year')
                ref_citation_count = ref.get('citationCount', 0)

                # 跳过没有 paperId 的引用
                if not ref_s2_id:
                    continue

                # 检查被引论文是否在用户图谱中
                is_internal = ref_s2_id in s2_to_doi

                citation_data = {
                    'citing_paper_id': paper_doi,
                    'cited_paper_id': s2_to_doi.get(ref_s2_id, ref_s2_id),  # 如果在图谱中用 DOI，否则用 S2 ID
                    'citing_s2_id': s2_id,
                    'cited_s2_id': ref_s2_id,
                    'citing_title': paper['title'],
                    'citing_year': paper.get('year'),
                    'cited_title': ref_title,
                    'cited_year': ref_year,
                    'cited_citation_count': ref_citation_count,
                    'is_internal': is_internal
                }

                db.add_paper_citation(citation_data)
                total_citations += 1
                if is_internal:
                    internal_edges += 1

            # 获取谁引用了这篇论文（被引）
            citations = s2_client.get_paper_citations(s2_id, limit=200)

            for cit in citations:
                cit_s2_id = cit.get('paperId')
                cit_title = cit.get('title')
                cit_year = cit.get('year')
                cit_citation_count = cit.get('citationCount', 0)

                # 跳过没有 paperId 的引用
                if not cit_s2_id:
                    continue

                # 检查引用论文是否在用户图谱中
                is_internal = cit_s2_id in s2_to_doi

                citation_data = {
                    'citing_paper_id': s2_to_doi.get(cit_s2_id, cit_s2_id),
                    'cited_paper_id': paper_doi,
                    'citing_s2_id': cit_s2_id,
                    'cited_s2_id': s2_id,
                    'citing_title': cit_title,
                    'citing_year': cit_year,
                    'cited_title': paper['title'],
                    'cited_year': paper.get('year'),
                    'cited_citation_count': paper.get('citation_count', 0),
                    'is_internal': is_internal
                }

                db.add_paper_citation(citation_data)
                total_citations += 1
                if is_internal:
                    internal_edges += 1

            processed += 1

        except Exception as e:
            error_msg = f"Failed to process {paper['title']}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    return {
        'total_papers': total,
        'processed': processed,
        'total_citations': total_citations,
        'internal_edges': internal_edges,
        'errors': errors
    }


def get_internal_citation_edges(db) -> List[Dict]:
    """
    获取所有 is_internal=True 的引用边

    Returns:
        [
            {
                "source": citing_paper_id,
                "target": cited_paper_id,
                "source_title": "...",
                "target_title": "..."
            }
        ]
    """
    return db.get_internal_citation_edges()


def get_citation_context(db, paper_id: str) -> Dict:
    """
    获取某篇论文的引用上下文

    Returns:
        {
            "paper_id": "...",
            "title": "...",
            "citation_count": 42,
            "references": [...],  # 这篇论文引用了谁
            "cited_by": [...]     # 谁引用了这篇论文
        }
    """
    paper = db.get_paper(paper_id)
    if not paper:
        return None

    # 获取这篇论文引用了谁
    references_raw = db.get_paper_citations(paper_id)
    references = []
    for r in references_raw:
        ref_paper = db.get_paper(r['cited_paper_id'])
        references.append({
            'paper_id': r['cited_paper_id'],
            'title': r.get('cited_title') or (ref_paper.get('title') if ref_paper else None),
            'year': r.get('cited_year'),
            'citation_count': r.get('cited_citation_count', 0),
            'is_internal': r.get('is_internal', False)
        })

    # 获取谁引用了这篇论文
    cited_by_raw = db.get_paper_cited_by(paper_id)
    cited_by = []
    for c in cited_by_raw:
        citing_paper = db.get_paper(c['citing_paper_id'])
        cited_by.append({
            'paper_id': c['citing_paper_id'],
            'title': citing_paper.get('title') if citing_paper else c.get('citing_s2_id'),
            'year': citing_paper.get('year') if citing_paper else None,
            'citation_count': citing_paper.get('citation_count', 0) if citing_paper else 0,
            'is_internal': c.get('is_internal', False)
        })

    return {
        'paper_id': paper_id,
        'title': paper.get('title'),
        'citation_count': paper.get('citation_count', 0),
        'references': references,
        'cited_by': cited_by
    }


def get_citation_graph_data(db) -> Dict:
    """
    获取引用图谱数据（节点 + 边 + 统计）

    Returns:
        {
            'nodes': [...],
            'edges': [...]
        }
    """
    # 获取所有本地论文作为节点
    papers = db.get_all_papers_basic()

    # 获取所有引用数据
    all_citations = db.get_all_citations()

    nodes = []
    node_ids = set()  # 用于跟踪已添加的节点
    node_info = {}  # 存储节点信息

    # 先添加本地论文节点
    for p in papers:
        node_ids.add(p['doi'])
        node_info[p['doi']] = {
            'title': p['title'],
            'year': p.get('year'),
            'citation_count': p.get('citation_count', 0),
            'is_internal': True
        }
        nodes.append({
            'id': p['doi'],
            'title': p['title'],
            'year': p.get('year'),
            'citation_count': p.get('citation_count', 0),
            'venue': p.get('venue'),
            'is_internal': True
        })

    # 第一遍：收集所有涉及的节点（源和目标）
    for c in all_citations:
        source_id = c.get('citing_paper_id')
        target_id = c.get('cited_paper_id')

        # 添加源节点（如果不存在）
        if source_id and source_id not in node_ids:
            node_ids.add(source_id)
            node_info[source_id] = {
                'title': c.get('citing_title'),
                'year': c.get('citing_year'),
                'citation_count': 0,
                'is_internal': False
            }
            nodes.append({
                'id': source_id,
                'title': c.get('citing_title'),
                'year': c.get('citing_year'),
                'citation_count': 0,
                'venue': None,
                'is_internal': False
            })

        # 添加目标节点（如果不存在）
        if target_id and target_id not in node_ids:
            node_ids.add(target_id)
            node_info[target_id] = {
                'title': c.get('cited_title'),
                'year': c.get('cited_year'),
                'citation_count': c.get('cited_citation_count', 0),
                'is_internal': False
            }
            nodes.append({
                'id': target_id,
                'title': c.get('cited_title'),
                'year': c.get('cited_year'),
                'citation_count': c.get('cited_citation_count', 0),
                'venue': None,
                'is_internal': False
            })

    # 第二遍：构建边
    edges = []
    for c in all_citations:
        source_id = c.get('citing_paper_id')
        target_id = c.get('cited_paper_id')

        if source_id in node_ids and target_id in node_ids:
            edges.append({
                'source': source_id,
                'target': target_id,
                'source_title': c.get('citing_title'),
                'target_title': c.get('cited_title'),
                'target_year': c.get('cited_year'),
                'target_citation_count': c.get('cited_citation_count', 0)
            })

    return {
        'nodes': nodes,
        'edges': edges
    }