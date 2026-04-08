# backend/services/research_service.py
"""
研究服务 - 研究点发现和论文推荐
"""

from typing import Dict, List, Optional
import json
import re
from mkg.database import Database
from mkg.semantic_scholar import S2Client
from mkg.llm import init_llm_from_db, get_llm_or_raise


class ResearchService:
    """研究点发现服务"""

    def __init__(self, db: Database, s2_client: S2Client = None):
        self.db = db
        self.s2_client = s2_client

    def discover_research_points(self, concept_id: str) -> Dict:
        """发现概念的研究点"""
        concept = self.db.concepts.get(concept_id)
        if not concept:
            return {"error": "Concept not found", "concept_id": concept_id}

        # 获取相关上下文
        children = self.db.concepts.get_children(concept_id)
        parents = self.db.concepts.get_parents(concept_id)
        papers = self.db.concepts.get_papers(concept_id)

        try:
            # 初始化 LLM
            init_llm_from_db(self.db)
            llm = get_llm_or_raise()

            # 构建提示
            prompt = self._build_research_prompt(concept, children, parents, papers)

            # 调用 LLM
            response = llm.invoke(prompt)

            return {
                "concept_id": concept_id,
                "concept_name": concept["text"],
                "research_points": self._parse_research_points(response.content)
            }
        except Exception as e:
            return {"error": str(e), "concept_id": concept_id}

    def search_papers_by_concept(self, concept_id: str, year: str = None,
                                  min_citations: int = None, limit: int = 10) -> Dict:
        """搜索概念相关论文"""
        concept = self.db.concepts.get(concept_id)
        if not concept:
            return {"error": "Concept not found", "concept_id": concept_id}

        if not self.s2_client:
            return {"error": "S2 client not configured", "concept_id": concept_id}

        try:
            # 使用 S2 搜索
            query = concept["text"]
            papers = self.s2_client.search_papers(query, limit=limit * 2)

            # 过滤
            if year:
                papers = [p for p in papers if str(p.get("year")) == year]
            if min_citations:
                papers = [p for p in papers if p.get("citationCount", 0) >= min_citations]

            papers = papers[:limit]

            return {
                "concept_id": concept_id,
                "concept_text": concept["text"],
                "papers": papers,
                "total": len(papers)
            }
        except Exception as e:
            return {"error": str(e), "concept_id": concept_id}

    def _build_research_prompt(self, concept: Dict, children: List, parents: List, papers: List) -> str:
        """构建研究点发现提示"""
        child_texts = [c['text'] for c in children[:5]]
        parent_texts = [p['text'] for p in parents[:3]]

        return f"""分析以下概念的研究机会：

概念：{concept['text']}
子概念：{', '.join(child_texts) if child_texts else '无'}
父概念：{', '.join(parent_texts) if parent_texts else '无'}
相关论文数：{len(papers)}

请提供 3-5 个研究点，每个研究点包含：
1. 标题
2. 研究假设
3. 简要描述
4. 研究方法建议

以 JSON 格式返回。"""

    def _parse_research_points(self, content: str) -> List[Dict]:
        """解析研究点"""
        points = []

        # 尝试解析 JSON
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            try:
                points = json.loads(json_match.group())
                return points
            except json.JSONDecodeError:
                pass

        # 简单解析
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