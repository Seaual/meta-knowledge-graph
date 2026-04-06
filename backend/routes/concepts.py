"""
Concept API routes
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from pydantic import BaseModel
import sys
from pathlib import Path
import os
import json
import asyncio
import uuid
import time

BATCH_SIZE = 10  # Batch size for LLM analysis

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mkg.database import Database
from mkg.graph import KnowledgeGraph
from mkg.pdf_parser import LLMConceptExtractor
from mkg.llm import init_llm_from_db
from mkg.dedup import ConceptDeduplicator
from mkg.semantic_scholar import S2Client
from backend.schemas import ConceptResponse, ConceptTreeNode, ConceptDetail

router = APIRouter(prefix="/api/concepts", tags=["concepts"])

_db = None
_graph = None
_extractor = None
_deduplicator = None


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


def get_extractor():
    """获取概念提取器实例"""
    global _extractor
    if _extractor is None:
        db = get_db()
        # 初始化 LLM
        init_llm_from_db(db)
        _extractor = LLMConceptExtractor()
    return _extractor


def get_deduplicator():
    """获取去重器实例"""
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = ConceptDeduplicator(get_db(), None)
    return _deduplicator


class ResearchPoint(BaseModel):
    """研究点模型"""
    title: str
    hypothesis: str  # 核心假设，格式："如果将 X 应用于 Y，可能解决 Z 问题"
    description: str
    discovery_method: str  # gap_filling | leaf_extension | bottleneck | transfer
    rationale: str
    related_concepts: List[str] = []
    difficulty: str  # low | medium | high
    difficulty_reason: str  # 难度依据
    novelty: str  # incremental | moderate | high
    potential_impact: str  # niche | broad | transformative


class ResearchPointResponse(BaseModel):
    """研究点发现响应"""
    concept_id: str
    concept_name: str
    research_points: List[ResearchPoint]
    analysis_context: dict


class DedupScanRequest(BaseModel):
    """去重扫描请求"""
    folder_id: str = 'default'


class DedupExecuteRequest(BaseModel):
    """去重执行请求"""
    scan_id: str
    merge_ids: List[str]


def _build_research_prompt(
    concept: dict,
    ancestors: List[dict],
    descendants: List[dict],
    siblings: List[dict],
    edge_nodes: List[dict],
    papers: List[dict],
    s2_context: str = ""
) -> str:
    """
    构建研究点发现提示词

    使用四种方法论发现研究机会：
    - 空白地带法：图谱中两个本应有联系的分支之间缺少连接
    - 末端延伸法：叶子节点代表最具体的技术，它们能否应用到其他分支
    - 瓶颈识别法：某节点连接大量子节点但自身缺少兄弟节点
    - 迁移应用法：一个分支的成熟方法能否迁移到另一个问题尚未解决的分支
    """
    # S2 领域热度数据部分
    s2_section = ""
    if s2_context:
        s2_section = f"""
## 领域热度数据（来自 Semantic Scholar）
{s2_context}
"""

    prompt = f"""<s>
你是一位拥有 20 年经验的科研导师，擅长从知识图谱的结构特征中识别研究机会。

你发现研究点的四种方法论：
- **空白地带法**：图谱中两个本应有联系的分支之间缺少连接 → 未被探索的交叉方向
- **末端延伸法**：叶子节点代表最具体的技术 → 它们能否应用到其他分支？
- **瓶颈识别法**：某节点连接大量子节点但自身缺少兄弟节点 → 可能是领域瓶颈
- **迁移应用法**：一个分支的成熟方法 → 能否迁移到另一个问题尚未解决的分支？
</s>

<task>
基于以下知识图谱结构信息，发现 3-5 个有价值的潜在研究方向。
优先寻找**跨分支的交叉创新点**，而非已有方向的简单延伸。
</task>

<context>
## 焦点概念
- 名称：{concept['text']}
- 层级：{concept.get('category', 'unknown')}
- 关联论文数：{concept.get('paper_count', 0)}

## 上游路径（从根到当前概念的祖先链 — 学科脉络）
{json.dumps([{'text': a.get('text', a.get('name', '')), 'category': a.get('category')} for a in ancestors], ensure_ascii=False, indent=2)}

## 下游分支（当前概念的后代 — 已有的研究细分）
{json.dumps([{'text': d.get('text', d.get('name', '')), 'category': d.get('category'), 'paper_count': d.get('paper_count', 0)} for d in descendants], ensure_ascii=False, indent=2)}

## 邻域节点（共享父节点的不同分支 — 平行研究方向）
{json.dumps([{'text': s.get('text', s.get('name', '')), 'category': s.get('category'), 'paper_count': s.get('paper_count', 0)} for s in siblings], ensure_ascii=False, indent=2)}

## 远端节点（图谱中距离较远的叶子 — 潜在跨领域连接机会）
{json.dumps([{'text': e.get('text', e.get('name', '')), 'category': e.get('category')} for e in edge_nodes], ensure_ascii=False, indent=2)}

## 相关论文
{json.dumps([{'title': p.get('title', ''), 'research_questions': p.get('keywords', [])} for p in papers], ensure_ascii=False, indent=2)}
{s2_section}</context>

<output_format>
输出 JSON 数组，每个研究点包含：

[
  {{
    "title": "研究点标题（15字以内）",
    "hypothesis": "核心假设（用'如果将 X 应用于 Y，可能解决 Z 问题'的句式）",
    "description": "详细描述（80-150字），含问题背景、方法思路、预期结果",
    "discovery_method": "gap_filling | leaf_extension | bottleneck | transfer",
    "rationale": "为什么图谱结构暗示了这个研究机会（引用具体节点关系）",
    "related_concepts": ["涉及的概念名称"],
    "difficulty": "low | medium | high",
    "difficulty_reason": "难度依据（一句话）",
    "novelty": "incremental | moderate | high",
    "potential_impact": "niche | broad | transformative"
  }}
]

评分标准：

difficulty:
- low：现有方法直接扩展，3-6 个月
- medium：需新方法或新数据，6-12 个月
- high：基础理论创新或大规模实验，1 年以上

novelty:
- incremental：已有方法的小幅改进
- moderate：已有方法创造性应用于新问题
- high：新的问题定义或理论框架

potential_impact:
- niche：特定子领域的小范围影响
- broad：对整个研究方向有推动
- transformative：可能改变领域基本范式
</output_format>

只输出 JSON 数组，不要其他内容。
"""
    return prompt


@router.get("/", response_model=List[ConceptResponse])
def list_concepts():
    """Get all concepts"""
    db = get_db()
    return db.get_all_concepts()


@router.get("/roots", response_model=List[ConceptResponse])
def get_root_concepts():
    """Get root concepts (no parents)"""
    db = get_db()
    return db.get_root_concepts()


@router.get("/tree")
def get_concept_tree(root_id: Optional[str] = None):
    """Get concept tree structure"""
    db = get_db()
    tree = db.get_concept_tree(root_id)
    return tree


@router.get("/search")
def search_concepts(q: str = Query(..., min_length=1)):
    """Search concepts by query"""
    graph = get_graph()
    return graph.search_concepts(q)


@router.get("/{concept_id}", response_model=ConceptDetail)
def get_concept(concept_id: str):
    """Get concept details with parents, children, and papers"""
    db = get_db()
    concept = db.get_concept(concept_id)

    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    parents = db.get_concept_parents(concept_id)
    children = db.get_concept_children(concept_id)
    papers = db.get_papers_by_concept(concept_id)

    return ConceptDetail(
        id=concept['id'],
        text=concept['text'],
        category=concept.get('category'),
        paper_count=concept.get('paper_count', 0),
        depth_cache=concept.get('depth_cache', -1),
        parents=parents,
        children=children,
        papers=[{"doi": p['doi'], "title": p['title']} for p in papers]
    )


@router.get("/{concept_id}/papers")
def get_concept_papers(concept_id: str, limit: int = 20):
    """Get papers associated with a concept"""
    db = get_db()
    papers = db.get_papers_by_concept(concept_id)
    return papers[:limit]


@router.get("/{concept_id}/search-papers")
def search_papers_by_concept(
    concept_id: str,
    year: str = "2023-2026",
    min_citations: int = 0,
    limit: int = 20
):
    """
    基于概念搜索 S2 论文

    优先使用英文概念名称搜索，如果没有则使用中文
    """
    db = get_db()
    s2_client = S2Client()

    # 获取概念
    concept = db.get_concept(concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    # 优先使用英文概念名称（更适合 S2 搜索）
    concept_text = concept.get('text_en') or concept['text']

    # 搜索论文
    results = s2_client.search_papers(
        query=concept_text,
        year=year,
        limit=limit,
        min_citation_count=min_citations
    )

    # 过滤已在图谱中的论文
    papers = db.get_papers_with_s2_id()
    existing_s2_ids = {p['s2_paper_id'] for p in papers if p.get('s2_paper_id')}
    filtered = [r for r in results if r.get('paperId') not in existing_s2_ids]

    return {
        "concept_id": concept_id,
        "concept_text": concept_text,  # 用于搜索的文本（英文优先）
        "concept_text_zh": concept.get('text'),  # 中文名称
        "concept_text_en": concept.get('text_en'),  # 英文名称
        "papers": filtered,
        "total": len(filtered)
    }


@router.get("/{concept_id}/children")
def get_concept_children(concept_id: str):
    """Get child concepts"""
    db = get_db()
    return db.get_concept_children(concept_id)


@router.get("/{concept_id}/parents")
def get_concept_parents(concept_id: str):
    """Get parent concepts"""
    db = get_db()
    return db.get_concept_parents(concept_id)


@router.get("/{concept_id}/research-points", response_model=ResearchPointResponse)
def discover_research_points(concept_id: str):
    """
    发现研究点

    分析流程：
    1. 追溯上游节点（祖先链）
    2. 发现下游节点（后代）
    3. 获取邻域节点（兄弟分支）
    4. 遍历边缘节点（叶子节点）
    5. 获取相关论文
    6. 调用LLM生成研究点建议
    """
    db = get_db()
    extractor = get_extractor()

    if not extractor:
        raise HTTPException(status_code=500, detail="LLM not configured. Please set ANTHROPIC_API_KEY, GOOGLE_API_KEY, or DASHSCOPE_API_KEY")

    # 获取概念信息
    concept = db.get_concept(concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    # 1. 追溯上游节点（祖先链）
    ancestors = []
    current_id = concept_id
    visited = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        parents = db.get_concept_parents(current_id)
        if parents:
            ancestors.extend(parents)
            current_id = parents[0]['id']
        else:
            break

    # 2. 获取下游节点（后代）
    def get_all_descendants(node_id, max_depth=5):
        descendants = []
        queue = [(node_id, 0)]
        visited_desc = set()
        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth or current in visited_desc:
                continue
            visited_desc.add(current)
            children = db.get_concept_children(current)
            for child in children:
                if child['id'] not in visited_desc:
                    descendants.append({**child, 'depth': depth + 1})
                    queue.append((child['id'], depth + 1))
        return descendants

    descendants = get_all_descendants(concept_id)

    # 3. 获取邻域节点（兄弟分支）- 共享父节点的不同分支
    siblings = []
    concept_parents = db.get_concept_parents(concept_id)
    if concept_parents:
        for parent in concept_parents:
            parent_children = db.get_concept_children(parent['id'])
            for sibling in parent_children:
                if sibling['id'] != concept_id and sibling['id'] not in [s['id'] for s in siblings]:
                    siblings.append(sibling)

    # 4. 获取边缘节点（叶子节点）- 没有子节点的概念
    all_concepts = db.get_all_concepts()
    edge_nodes = []
    for c in all_concepts:
        children = db.get_concept_children(c['id'])
        if not children and c['id'] != concept_id:
            edge_nodes.append(c)

    # 5. 获取相关论文
    papers = db.get_papers_by_concept(concept_id)
    paper_info = []
    for p in papers[:5]:  # 取前5篇论文
        paper_info.append({
            'title': p.get('title', ''),
            'abstract': (p.get('abstract') or '')[:500],  # 截取前500字
            'keywords': p.get('keywords', []),
        })

    # 6. 构建分析上下文
    context = {
        'concept': {
            'id': concept_id,
            'text': concept['text'],
            'name': concept['text'],  # 兼容旧字段名
            'category': concept.get('category'),
            'paper_count': concept.get('paper_count', 0),
        },
        'ancestors': ancestors[:5],
        'descendants': descendants[:10],
        'siblings': siblings[:10],
        'edge_nodes': edge_nodes[:15],
        'related_papers': paper_info,
    }

    # 6.5 收集 S2 领域热度数据（新增）
    s2_context = ""
    try:
        from mkg.semantic_scholar import S2Client
        s2_client = S2Client()

        # 用概念名称搜索相关论文
        search_results = s2_client.search_papers(
            concept['text'],
            year="2020-2026",
            limit=100,
            min_citation_count=0
        )

        if search_results:
            total = len(search_results)
            recent = len([p for p in search_results if p.get('year', 0) >= 2024])
            avg_citations = sum(p.get('citationCount', 0) for p in search_results) / total if total > 0 else 0

            # 找最高被引论文
            top_paper = max(search_results, key=lambda p: p.get('citationCount', 0)) if search_results else None

            # 计算年度趋势
            by_year = {}
            for p in search_results:
                y = p.get('year', 0)
                if y > 0:
                    by_year[y] = by_year.get(y, 0) + 1

            years_sorted = sorted(by_year.keys())
            if len(years_sorted) >= 2:
                recent_avg = sum(by_year.get(y, 0) for y in years_sorted[-2:]) / 2
                earlier_avg = sum(by_year.get(y, 0) for y in years_sorted[:-2]) / max(len(years_sorted) - 2, 1)
                if recent_avg > earlier_avg * 1.2:
                    trend = "rising (上升趋势)"
                elif recent_avg < earlier_avg * 0.8:
                    trend = "declining (下降趋势)"
                else:
                    trend = "stable (稳定)"
            else:
                trend = "unknown (数据不足)"

            s2_context = f"""- 概念 "{concept['text']}" 相关论文搜索结果：{total} 篇
- 2024-2026 年新论文：{recent} 篇（占比 {recent*100//total if total > 0 else 0}%）
- 平均引用数：{avg_citations:.1f}
- 年度趋势：{trend}
- 最高被引论文："{top_paper.get('title', 'N/A')}" ({top_paper.get('citationCount', 0)} citations, {top_paper.get('year', '?')})
- 年度分布：{json.dumps(by_year, ensure_ascii=False)}"""
        else:
            s2_context = "未找到相关论文，可能是较新或较冷门的方向。"

    except Exception as e:
        print(f"S2 search failed for research points: {e}")
        s2_context = f"领域热度数据获取失败: {str(e)}"

    # 7. 构建提示词并调用LLM分析
    prompt = _build_research_prompt(
        concept=context['concept'],
        ancestors=context['ancestors'],
        descendants=context['descendants'],
        siblings=context['siblings'],
        edge_nodes=context['edge_nodes'],
        papers=paper_info,
        s2_context=s2_context
    )

    try:
        # 调用LLM
        response = extractor.api_client.generate(prompt)

        # 解析响应
        # 尝试提取JSON
        response_text = response.strip()

        # 处理代码块标记 (```json 或 ```)
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            # 跳过第一行（可能是 ```json 或 ```）
            # 跳过最后一行（如果是 ```）
            start_idx = 1
            end_idx = len(lines)
            if lines[-1].strip() == '```':
                end_idx = len(lines) - 1
            response_text = '\n'.join(lines[start_idx:end_idx])

        research_points_data = json.loads(response_text)

        # 转换为 ResearchPoint 模型
        research_points = []
        for rp in research_points_data:
            research_points.append(ResearchPoint(
                title=rp.get('title', ''),
                hypothesis=rp.get('hypothesis', ''),
                description=rp.get('description', ''),
                discovery_method=rp.get('discovery_method', 'gap_filling'),
                rationale=rp.get('rationale', ''),
                related_concepts=rp.get('related_concepts', []),
                difficulty=rp.get('difficulty', 'medium'),
                difficulty_reason=rp.get('difficulty_reason', ''),
                novelty=rp.get('novelty', 'moderate'),
                potential_impact=rp.get('potential_impact', 'niche'),
            ))

        return ResearchPointResponse(
            concept_id=concept_id,
            concept_name=concept['text'],
            research_points=research_points,
            analysis_context=context,
        )
    except json.JSONDecodeError as e:
        # 如果解析失败，返回默认结构
        return ResearchPointResponse(
            concept_id=concept_id,
            concept_name=concept['text'],
            research_points=[ResearchPoint(
                title="研究点分析",
                hypothesis="LLM返回格式异常，请重试",
                description="LLM返回格式异常，请重试",
                discovery_method="gap_filling",
                rationale=str(e),
                related_concepts=[],
                difficulty="medium",
                difficulty_reason="解析错误",
                novelty="incremental",
                potential_impact="niche",
            )],
            analysis_context=context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM analysis failed: {str(e)}")


@router.post("/dedup/scan")
async def start_dedup_scan(request: DedupScanRequest):
    """
    Start async deduplication scan

    Returns scan_id for polling progress
    """
    db = get_db()
    deduplicator = get_deduplicator()

    if not deduplicator.merge_analyzer:
        raise HTTPException(
            status_code=500,
            detail="LLM not configured. Please set ANTHROPIC_API_KEY, GOOGLE_API_KEY, or DASHSCOPE_API_KEY"
        )

    # Clean up old jobs
    db.cleanup_old_scan_jobs()

    # Create scan job
    scan_id = f"scan-{uuid.uuid4().hex[:8]}"
    total_concepts = db.get_concept_count(folder_id=request.folder_id)
    db.create_scan_job(scan_id, total_concepts)

    # Start background task
    asyncio.create_task(run_dedup_scan_background(scan_id, request.folder_id))

    return {
        "scan_id": scan_id,
        "total_concepts": total_concepts,
        "status": "scanning"
    }


async def run_dedup_scan_background(scan_id: str, folder_id: str = 'default'):
    """Background task for dedup scan with batch processing"""
    try:
        db = get_db()
        deduplicator = get_deduplicator()

        # Phase 1: Pre-filtering
        db.update_scan_job(scan_id, status='scanning', phase='prefiltering', started_at=time.time())

        prefiltered = deduplicator.candidate_generator.generate_candidates_with_prefilter(folder_id=folder_id)

        candidates = prefiltered['candidates']
        high_confidence = prefiltered['high_confidence']
        stats = prefiltered['stats']

        # Update job with prefilter stats
        total_batches = (len(candidates) + BATCH_SIZE - 1) // BATCH_SIZE if candidates else 0
        db.update_scan_job(
            scan_id,
            phase='analyzing',
            total_concepts=len(candidates),
            batches_total=total_batches,
            filtered_count=stats.get('filtered', 0),
            high_confidence_count=len(high_confidence)
        )

        if not candidates and not high_confidence:
            db.update_scan_job(
                scan_id,
                status='completed',
                phase='completed',
                suggestions=[],
                completed_at=time.time()
            )
            return

        # Prepare analyzer
        deduplicator.merge_analyzer._get_parent_names = lambda cid: [p['id'] for p in db.get_concept_parents(cid)]
        deduplicator.merge_analyzer._get_child_names = lambda cid: [c['id'] for c in db.get_concept_children(cid)]

        # Phase 2: Batch LLM analysis
        suggestions = []

        # Add high confidence suggestions first
        for i, hc in enumerate(high_confidence):
            source = db.get_concept(hc['source_id'])
            target = db.get_concept(hc['target_id'])
            if source and target:
                suggestions.append({
                    "id": f"merge-{scan_id}-{len(suggestions)}",
                    "source": {"id": source['id'], "text": source['text'], "paper_count": source.get('paper_count', 0)},
                    "target": {"id": target['id'], "text": target['text'], "paper_count": target.get('paper_count', 0)},
                    "confidence": hc['confidence'],
                    "rationale": hc['rationale'],
                    "merge_type": hc.get('merge_type', 'synonym')
                })

        # Process candidates in batches
        batches_completed = 0
        for batch_start in range(0, len(candidates), BATCH_SIZE):
            batch = candidates[batch_start:batch_start + BATCH_SIZE]

            try:
                # Batch LLM call
                batch_suggestions = deduplicator.merge_analyzer.analyze(batch)

                if batch_suggestions:
                    for s in batch_suggestions:
                        source = db.get_concept(s.source_id)
                        target = db.get_concept(s.target_id)
                        if source and target:
                            suggestions.append({
                                "id": f"merge-{scan_id}-{len(suggestions)}",
                                "source": {"id": source['id'], "text": source['text'], "paper_count": source.get('paper_count', 0)},
                                "target": {"id": target['id'], "text": target['text'], "paper_count": target.get('paper_count', 0)},
                                "confidence": s.confidence,
                                "rationale": s.rationale,
                                "merge_type": s.merge_type
                            })

            except Exception as e:
                # Batch failed - try individual analysis as fallback
                print(f"Batch analysis failed, falling back to individual: {e}")
                for candidate in batch:
                    try:
                        result = deduplicator.merge_analyzer.analyze([candidate])
                        if result:
                            for s in result:
                                source = db.get_concept(s.source_id)
                                target = db.get_concept(s.target_id)
                                if source and target:
                                    suggestions.append({
                                        "id": f"merge-{scan_id}-{len(suggestions)}",
                                        "source": {"id": source['id'], "text": source['text'], "paper_count": source.get('paper_count', 0)},
                                        "target": {"id": target['id'], "text": target['text'], "paper_count": target.get('paper_count', 0)},
                                        "confidence": s.confidence,
                                        "rationale": s.rationale,
                                        "merge_type": s.merge_type
                                    })
                    except Exception as e2:
                        print(f"Individual analysis also failed: {e2}")

            # Update progress after each batch
            batches_completed += 1
            db.update_scan_job(
                scan_id,
                concepts_scanned=min(batch_start + BATCH_SIZE, len(candidates)),
                batches_completed=batches_completed
            )

        # Phase 3: Complete
        db.update_scan_job(
            scan_id,
            status='completed',
            phase='completed',
            suggestions=suggestions,
            completed_at=time.time()
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        db = get_db()
        db.update_scan_job(scan_id, status='failed', phase='failed', error=str(e), completed_at=time.time())


@router.get("/dedup/scan-status/{scan_id}")
def get_dedup_scan_status(scan_id: str):
    """
    Get dedup scan progress

    Returns progress and estimated time remaining
    """
    db = get_db()
    job = db.get_scan_job(scan_id)

    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")

    # Calculate estimated time
    estimated_time = 0
    started_at = job.get('started_at')
    if job['concepts_scanned'] > 0 and job['total_concepts'] > 0 and started_at:
        try:
            started_at_float = float(started_at)
            elapsed = time.time() - started_at_float
            if elapsed > 0:
                avg_time = elapsed / job['concepts_scanned']
                remaining = job['total_concepts'] - job['concepts_scanned']
                estimated_time = int(avg_time * remaining)
        except (TypeError, ValueError):
            pass

    # Calculate progress
    progress = 0
    if job['total_concepts'] > 0:
        progress = (job['concepts_scanned'] / job['total_concepts']) * 100

    return {
        "scan_id": scan_id,
        "status": job['status'],
        "phase": job.get('phase', 'unknown'),
        "total_concepts": job['total_concepts'],
        "concepts_scanned": job['concepts_scanned'],
        "batches_total": job.get('batches_total', 0),
        "batches_completed": job.get('batches_completed', 0),
        "filtered_count": job.get('filtered_count', 0),
        "high_confidence_count": job.get('high_confidence_count', 0),
        "progress": progress,
        "estimated_time": estimated_time,
        "suggestions": job.get('suggestions') if job['status'] == 'completed' else None,
        "error": job.get('error')
    }


@router.post("/dedup/execute")
def dedup_execute(request: DedupExecuteRequest):
    """
    执行合并操作

    用户确认后执行指定的合并建议
    """
    deduplicator = get_deduplicator()

    result = deduplicator.execute_merge(request.scan_id, request.merge_ids)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result