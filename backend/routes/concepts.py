"""
Concept API routes
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
import sys
from pathlib import Path
import os
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from openclaw.database import Database
from openclaw.graph import KnowledgeGraph
from openclaw.pdf_parser import LLMConceptExtractor, AnthropicClient, GoogleClient, OpenAICompatibleClient, ClaudeCLIClient
from openclaw.dedup import ConceptDeduplicator
from backend.schemas import ConceptResponse, ConceptTreeNode, ConceptDetail

router = APIRouter(prefix="/api/concepts", tags=["concepts"])

_db = None
_graph = None
_extractor = None
_deduplicator = None


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


def get_extractor():
    global _extractor
    if _extractor is None:
        db = get_db()

        # Try database config first
        config = db.get_llm_config()
        if config and config.get('providers'):
            provider_config = None
            if config['mode'] == 'per_function':
                # For concepts, use concept_analysis or default to first
                provider_config = db.get_llm_provider_for_function('concept_analysis')
                if not provider_config:
                    provider_config = config['providers'][0]
            else:
                provider_config = db.get_active_llm_provider()
                if not provider_config:
                    provider_config = config['providers'][0]

            if provider_config:
                _extractor = _create_client_from_config(provider_config)
                return _extractor

        # Fallback: try Claude CLI first (leverage Claude Code's configured API)
        try:
            _extractor = LLMConceptExtractor(ClaudeCLIClient())
            return _extractor
        except Exception as e:
            print(f"Claude CLI not available: {e}")

        # Fallback to environment variables
        _extractor = _create_client_from_env()
        return _extractor
    return _extractor


def _create_client_from_config(config: dict):
    """Create LLM client from database config"""
    provider = config.get('provider')
    api_key = config.get('api_key')
    base_url = config.get('base_url')
    model = config.get('model')

    if provider == 'claude_cli':
        return LLMConceptExtractor(ClaudeCLIClient())
    elif provider == 'anthropic':
        return LLMConceptExtractor(AnthropicClient(api_key, model=model or 'claude-sonnet-4-20250514', base_url=base_url))
    elif provider == 'google':
        return LLMConceptExtractor(GoogleClient(api_key))
    else:  # openai, dashscope, openrouter, minimax
        default_urls = {
            'dashscope': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            'openrouter': 'https://openrouter.ai/api/v1',
        }
        return LLMConceptExtractor(OpenAICompatibleClient(
            api_key,
            base_url=base_url or default_urls.get(provider),
            model=model
        ))


def _create_client_from_env():
    """Create LLM client from environment variables"""
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        return None
    if os.getenv("ANTHROPIC_API_KEY"):
        client = AnthropicClient(api_key)
    elif os.getenv("GOOGLE_API_KEY"):
        client = GoogleClient(api_key)
    else:
        client = OpenAICompatibleClient(api_key)
    return LLMConceptExtractor(client)


def get_deduplicator():
    """获取去重器实例"""
    global _deduplicator
    if _deduplicator is None:
        extractor = get_extractor()
        _deduplicator = ConceptDeduplicator(get_db(), extractor.api_client if extractor else None)
    return _deduplicator


class ResearchPointResponse(BaseModel):
    """研究点发现响应"""
    concept_id: str
    concept_name: str
    research_points: List[dict]
    analysis_context: dict


class DedupExecuteRequest(BaseModel):
    """去重执行请求"""
    scan_id: str
    merge_ids: List[str]


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
    1. 追溯上游节点（父概念链）
    2. 发现下游节点及其相关性
    3. 遍历边缘节点，找可结合的点
    4. 调用LLM生成研究点建议
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

    # 3. 获取边缘节点（叶子节点）- 没有子节点的概念
    all_concepts = db.get_all_concepts()
    edge_nodes = []
    for c in all_concepts:
        children = db.get_concept_children(c['id'])
        if not children and c['id'] != concept_id:
            edge_nodes.append(c)

    # 4. 获取相关论文
    papers = db.get_papers_by_concept(concept_id)
    paper_info = []
    for p in papers[:5]:  # 取前5篇论文
        paper_info.append({
            'title': p.get('title', ''),
            'abstract': (p.get('abstract') or '')[:500],  # 截取前500字
            'keywords': p.get('keywords', []),
        })

    # 5. 构建分析上下文
    context = {
        'concept': {
            'id': concept_id,
            'name': concept['text'],
            'category': concept.get('category'),
        },
        'ancestors': [{'id': a['id'], 'name': a['text'], 'category': a.get('category')} for a in ancestors[:5]],
        'descendants': [{'id': d['id'], 'name': d['text'], 'category': d.get('category'), 'depth': d.get('depth')} for d in descendants[:10]],
        'edge_nodes': [{'id': e['id'], 'name': e['text'], 'category': e.get('category')} for e in edge_nodes[:15]],
        'related_papers': paper_info,
    }

    # 6. 调用LLM分析
    prompt = f"""你是一个学术研究顾问。请基于以下知识图谱信息，发现潜在的研究点。

## 当前概念
- 名称: {concept['text']}
- 类别: {concept.get('category', 'unknown')}

## 上游概念链（研究领域的发展脉络）
{json.dumps([a['name'] for a in context['ancestors']], ensure_ascii=False, indent=2)}

## 下游概念（具体研究方向和方法）
{json.dumps([d['name'] for d in context['descendants']], ensure_ascii=False, indent=2)}

## 边缘节点（其他研究分支的末端概念）
{json.dumps([e['name'] for e in context['edge_nodes']], ensure_ascii=False, indent=2)}

## 相关论文
{json.dumps([{'title': p['title'], 'keywords': p['keywords']} for p in paper_info], ensure_ascii=False, indent=2)}

请分析以上信息，发现3-5个潜在的研究点。对于每个研究点，请提供：
1. title: 研究点标题
2. description: 研究点描述（50-100字）
3. rationale: 为什么这是一个有价值的研究点
4. related_concepts: 相关的概念列表
5. difficulty: 研究难度（easy/medium/hard）
6. potential_impact: 潜在影响（low/medium/high）

请以JSON数组格式返回结果，不要添加任何其他文字说明。
"""

    try:
        # 调用LLM
        response = extractor.api_client.generate(prompt)

        # 解析响应
        # 尝试提取JSON
        response_text = response.strip()
        if response_text.startswith('```'):
            # 去除代码块标记
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])

        research_points = json.loads(response_text)

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
            research_points=[{
                "title": "研究点分析",
                "description": "LLM返回格式异常，请重试",
                "rationale": str(e),
                "related_concepts": [],
                "difficulty": "unknown",
                "potential_impact": "unknown",
            }],
            analysis_context=context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM analysis failed: {str(e)}")


@router.post("/dedup/scan")
def dedup_scan():
    """
    触发去重扫描

    返回候选合并建议列表，需要用户确认后才执行合并
    """
    deduplicator = get_deduplicator()

    if not deduplicator.merge_analyzer:
        raise HTTPException(
            status_code=500,
            detail="LLM not configured. Please set ANTHROPIC_API_KEY, GOOGLE_API_KEY, or DASHSCOPE_API_KEY"
        )

    result = deduplicator.scan()
    return result


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