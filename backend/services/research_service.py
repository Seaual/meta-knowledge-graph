# backend/services/research_service.py
"""
研究服务 - 研究点发现和论文推荐
"""

import json
import logging
import re

from mkg.database import Database
from mkg.llm import extract_text_content, get_llm_or_raise, init_llm_from_db
from mkg.resilience import RetryableExternalError, call_with_retries
from mkg.semantic_scholar import S2Client

logger = logging.getLogger(__name__)


class ResearchService:
    """研究点发现服务"""

    def __init__(self, db: Database, s2_client: S2Client = None):
        self.db = db
        self.s2_client = s2_client

    def _get_children(self, concept_id: str) -> list[dict]:
        """获取子概念，优先 Neo4j"""
        neo4j = self.db.neo4j_store
        if neo4j and neo4j.connected:
            results = neo4j.get_children(concept_id)
            if results is not None:
                return results
        return self.db.concepts.get_children(concept_id)

    def _get_parents(self, concept_id: str) -> list[dict]:
        """获取父概念，优先 Neo4j"""
        neo4j = self.db.neo4j_store
        if neo4j and neo4j.connected:
            results = neo4j.get_parents(concept_id)
            if results is not None:
                return results
        return self.db.concepts.get_parents(concept_id)

    def _get_siblings(self, concept_id: str) -> list[dict]:
        """获取兄弟概念（共享父节点的不同分支）"""
        parents = self._get_parents(concept_id)
        siblings = []
        for parent in parents:
            children = self._get_children(parent['id'])
            for sibling in children:
                if sibling['id'] != concept_id and sibling['id'] not in [s['id'] for s in siblings]:
                    siblings.append(sibling)
        return siblings

    def _get_edge_nodes(self, concept_id: str) -> list[dict]:
        """获取边缘节点（叶子节点）"""
        all_concepts = self.db.concepts.get_all()
        edge_nodes = []
        for c in all_concepts:
            children = self._get_children(c['id'])
            if not children and c['id'] != concept_id:
                edge_nodes.append(c)
        return edge_nodes[:15]

    def discover_research_points(self, concept_id: str) -> dict:
        """发现概念的研究点"""
        concept = self.db.concepts.get(concept_id)
        if not concept:
            return {"error": "Concept not found", "concept_id": concept_id}

        # 获取完整上下文
        children = self._get_children(concept_id)
        parents = self._get_parents(concept_id)
        siblings = self._get_siblings(concept_id)[:10]
        edge_nodes = self._get_edge_nodes(concept_id)
        papers = self.db.concepts.get_papers(concept_id)

        # 构建祖先链
        ancestors = []
        current_id = concept_id
        visited = set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            current_parents = self._get_parents(current_id)
            if current_parents:
                ancestors.extend(current_parents)
                current_id = current_parents[0]['id']
            else:
                break

        # 构建后代（BFS）
        def get_all_descendants(node_id, max_depth=5):
            descendants = []
            queue = [(node_id, 0)]
            visited_desc = set()
            while queue:
                current, depth = queue.pop(0)
                if depth >= max_depth or current in visited_desc:
                    continue
                visited_desc.add(current)
                current_children = self._get_children(current)
                for child in current_children:
                    if child['id'] not in visited_desc:
                        descendants.append({**child, 'depth': depth + 1})
                        queue.append((child['id'], depth + 1))
            return descendants

        descendants = get_all_descendants(concept_id)[:10]

        # 论文信息
        paper_info = []
        for p in papers[:5]:
            paper_info.append({
                'title': p.get('title', ''),
                'abstract': (p.get('abstract') or '')[:500],
                'keywords': p.get('keywords', []),
            })

        try:
            # 初始化 LLM
            init_llm_from_db(self.db)
            llm = get_llm_or_raise()

            # 构建提示词
            concept_data = {
                'text': concept['text'],
                'text_en': concept.get('text_en'),
                'category': concept.get('category'),
                'paper_count': concept.get('paper_count', 0),
            }
            prompt = self._build_research_prompt(
                concept=concept_data,
                ancestors=ancestors[:5],
                descendants=descendants,
                siblings=siblings,
                edge_nodes=edge_nodes,
                papers=paper_info,
            )

            # 调用 LLM
            def _invoke():
                try:
                    return llm.invoke(prompt)
                except Exception as exc:
                    error_text = str(exc).lower()
                    if any(token in error_text for token in ("timeout", "timed out", "rate limit", "429", "503")):
                        raise RetryableExternalError(str(exc)) from exc
                    raise

            response = call_with_retries(
                "research_service.discover_research_points",
                _invoke,
                logger=logger,
                retries=2,
                retry_delay=1.5,
            )
            content = extract_text_content(response.content if hasattr(response, "content") else response)

            return {
                "concept_id": concept_id,
                "concept_name": concept.get("text_en") or concept["text"],
                "research_points": self._parse_research_points(content),
                "analysis_context": {
                    "concept": concept_data,
                    "ancestors": ancestors[:5],
                    "descendants": descendants,
                    "siblings": siblings,
                    "edge_nodes": edge_nodes,
                    "related_papers": paper_info,
                },
            }
        except Exception as e:
            return {"error": str(e), "concept_id": concept_id}

    def search_papers_by_concept(self, concept_id: str, year: str = None,
                                  min_citations: int = None, limit: int = 10) -> dict:
        """搜索概念相关论文"""
        concept = self.db.concepts.get(concept_id)
        if not concept:
            return {"error": "Concept not found", "concept_id": concept_id}

        if not self.s2_client:
            return {"error": "S2 client not configured", "concept_id": concept_id}

        # 如果概念缺少英文名，自动翻译
        if not concept.get("text_en"):
            from backend.services.concept_translation import translate_concept_if_needed
            en_name = translate_concept_if_needed(concept, self.db)
            concept["text_en"] = en_name  # 更新内存中的概念，避免重新查询数据库

        try:
            # 始终使用英文概念名搜索 Semantic Scholar
            query = concept.get("text_en") or concept["text"]
            papers = self.s2_client.search_papers(query, limit=limit * 2)

            # 过滤
            if year:
                papers = [p for p in papers if str(p.get("year")) == year]
            if min_citations:
                papers = [p for p in papers if p.get("citationCount", 0) >= min_citations]

            papers = papers[:limit]

            return {
                "concept_id": concept_id,
                "concept_text": concept.get("text_en") or concept["text"],
                "papers": papers,
                "total": len(papers)
            }
        except Exception as e:
            return {"error": str(e), "concept_id": concept_id}

    def _build_research_prompt(
        self,
        concept: dict,
        ancestors: list,
        descendants: list,
        siblings: list,
        edge_nodes: list,
        papers: list,
    ) -> str:
        """构建研究点发现提示词 — 四种方法论"""

        def _localized_name(c):
            return c.get("text_en") or c.get("text", "")

        return f"""<s>
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
- 名称：{_localized_name(concept)}
- 层级：{concept.get('category', 'unknown')}
- 关联论文数：{concept.get('paper_count', 0)}

## 上游路径（从根到当前概念的祖先链 — 学科脉络）
{json.dumps([{'text': _localized_name(a), 'category': a.get('category')} for a in ancestors], ensure_ascii=False, indent=2)}

## 下游分支（当前概念的后代 — 已有的研究细分）
{json.dumps([{'text': _localized_name(d), 'category': d.get('category'), 'paper_count': d.get('paper_count', 0)} for d in descendants], ensure_ascii=False, indent=2)}

## 邻域节点（共享父节点的不同分支 — 平行研究方向）
{json.dumps([{'text': _localized_name(s), 'category': s.get('category'), 'paper_count': s.get('paper_count', 0)} for s in siblings], ensure_ascii=False, indent=2)}

## 远端节点（图谱中距离较远的叶子 — 潜在跨领域连接机会）
{json.dumps([{'text': _localized_name(e), 'category': e.get('category')} for e in edge_nodes], ensure_ascii=False, indent=2)}

## 相关论文
{json.dumps([{'title': p.get('title', ''), 'research_questions': p.get('keywords', [])} for p in papers], ensure_ascii=False, indent=2)}
</context>

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

    def _parse_research_points(self, content: str) -> list[dict]:
        """解析研究点"""
        points = []

        # 中文键名到英文键名的映射
        KEY_MAP = {
            "标题": "title",
            "研究假设": "hypothesis",
            "简要描述": "description",
            "研究方法建议": "methods",
            "发现方法": "discovery_method",
            "相关概念": "related_concepts",
            "难度": "difficulty",
            "难度依据": "difficulty_reason",
            "新颖性": "novelty",
        }

        # 尝试解析 JSON
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            try:
                raw_points = json.loads(json_match.group())
                # 标准化键名（中文→英文）
                for raw in raw_points:
                    if isinstance(raw, dict):
                        point = {}
                        for k, v in raw.items():
                            en_key = KEY_MAP.get(k, k)
                            point[en_key] = v
                        points.append(point)
                    else:
                        points.append({"title": str(raw)})
                return points
            except json.JSONDecodeError:
                pass

        # 简单解析（fallback）
        lines = content.split("\n")
        current = None

        for line in lines:
            if line.startswith("##") or line.startswith("**") or re.match(r'^\d+\.', line):
                if current:
                    points.append(current)
                title = re.sub(r'^[#*>\d.\s]+', '', line).strip()
                current = {"title": title, "description": ""}
            elif current and line.strip():
                current["description"] += line.strip() + " "

        if current:
            points.append(current)

        return points[:5]
