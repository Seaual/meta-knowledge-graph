# mkg/agent/research_agent.py
"""
Research Point Agent - 分析概念研究点
"""

import json
from typing import Dict, Any, Optional, List
from .prompts import RESEARCH_POINT_FOLLOWUP_PROMPT


class ResearchPointAgent:
    """研究点分析 Agent"""

    def __init__(self, llm_client, db, s2_client=None):
        """
        初始化 Research Point Agent

        Args:
            llm_client: LLM 客户端
            db: Database 实例
            s2_client: S2 API 客户端（可选）
        """
        self.llm_client = llm_client
        self.db = db
        self.s2_client = s2_client

    def analyze(self, concept_identifier: str) -> Dict[str, Any]:
        """
        分析概念的研究点

        Args:
            concept_identifier: 概念 ID 或名称

        Returns:
            分析结果字典
        """
        # 1. 获取概念信息
        concept = self._get_concept(concept_identifier)
        if not concept:
            return {'error': f'无法找到概念: {concept_identifier}'}

        concept_id = concept['id']
        concept_name = concept['text']

        # 2. 获取图谱结构
        ancestors = self._get_ancestors(concept_id)
        descendants = self._get_descendants(concept_id)
        siblings = self._get_siblings(concept_id)
        papers = self._get_papers(concept_id)

        # 3. 获取 S2 热度数据
        s2_context = ""
        if self.s2_client:
            s2_context = self._get_s2_trend(concept_name)

        # 4. 构建分析上下文
        context = {
            'concept': {
                'id': concept_id,
                'name': concept_name,
                'category': concept.get('category'),
                'paper_count': concept.get('paper_count', 0),
            },
            'ancestors': ancestors[:5],
            'descendants': descendants[:10],
            'siblings': siblings[:10],
            'papers': papers[:5],
            's2_context': s2_context,
        }

        # 5. 调用现有的研究点发现 API
        research_points = self._discover_research_points(concept_id)

        return {
            'concept': context['concept'],
            'structure': {
                'ancestors': ancestors[:5],
                'descendants': descendants[:10],
                'siblings': siblings[:10],
            },
            'research_points': research_points,
            's2_context': s2_context,
        }

    def _get_concept(self, identifier: str) -> Optional[Dict]:
        """获取概念信息"""
        # 先尝试作为 ID
        concept = self.db.get_concept(identifier)
        if concept:
            return concept

        # 尝试作为名称搜索
        concepts = self.db.get_all_concepts()
        for c in concepts:
            if c['text'].lower() == identifier.lower():
                return c
        return None

    def _get_ancestors(self, concept_id: str) -> List[Dict]:
        """获取祖先节点"""
        ancestors = []
        current_id = concept_id
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            parents = self.db.get_concept_parents(current_id)
            if parents:
                ancestors.extend(parents)
                current_id = parents[0]['id']
            else:
                break

        return ancestors

    def _get_descendants(self, concept_id: str, max_depth: int = 3) -> List[Dict]:
        """获取后代节点"""
        descendants = []
        queue = [(concept_id, 0)]
        visited = set()

        while queue:
            current_id, depth = queue.pop(0)
            if depth >= max_depth or current_id in visited:
                continue
            visited.add(current_id)

            children = self.db.get_concept_children(current_id)
            for child in children:
                if child['id'] not in visited:
                    descendants.append({**child, 'depth': depth + 1})
                    queue.append((child['id'], depth + 1))

        return descendants

    def _get_siblings(self, concept_id: str) -> List[Dict]:
        """获取兄弟节点"""
        siblings = []
        parents = self.db.get_concept_parents(concept_id)

        for parent in parents:
            children = self.db.get_concept_children(parent['id'])
            for child in children:
                if child['id'] != concept_id and child not in siblings:
                    siblings.append(child)

        return siblings

    def _get_papers(self, concept_id: str, limit: int = 5) -> List[Dict]:
        """获取关联论文"""
        papers = self.db.get_papers_by_concept(concept_id)
        return papers[:limit]

    def _get_s2_trend(self, concept_name: str) -> str:
        """获取 S2 热度数据"""
        if not self.s2_client:
            return ""

        try:
            results = self.s2_client.search_papers(
                concept_name,
                year="2020-2026",
                limit=50,
                min_citation_count=0
            )

            if not results:
                return "未找到相关论文"

            total = len(results)
            recent = len([p for p in results if p.get('year', 0) >= 2024])
            avg_citations = sum(p.get('citationCount', 0) for p in results) / total if total > 0 else 0

            # 计算趋势
            by_year = {}
            for p in results:
                y = p.get('year', 0)
                if y > 0:
                    by_year[y] = by_year.get(y, 0) + 1

            years_sorted = sorted(by_year.keys())
            if len(years_sorted) >= 2:
                recent_avg = sum(by_year.get(y, 0) for y in years_sorted[-2:]) / 2
                earlier_avg = sum(by_year.get(y, 0) for y in years_sorted[:-2]) / max(len(years_sorted) - 2, 1)
                if recent_avg > earlier_avg * 1.2:
                    trend = "上升趋势"
                elif recent_avg < earlier_avg * 0.8:
                    trend = "下降趋势"
                else:
                    trend = "稳定"
            else:
                trend = "数据不足"

            return f"相关论文: {total} 篇 | 2024-2026 新论文: {recent} 篇 | 平均引用: {avg_citations:.1f} | 趋势: {trend}"

        except Exception as e:
            return f"S2 数据获取失败: {str(e)}"

    def _discover_research_points(self, concept_id: str) -> List[Dict]:
        """发现研究点（复用现有 API 逻辑）"""
        from mkg.pdf_parser import LiteLLMClient

        # 获取概念信息
        concept = self.db.get_concept(concept_id)
        if not concept:
            return []

        # 获取上下文
        ancestors = self._get_ancestors(concept_id)
        descendants = self._get_descendants(concept_id)
        siblings = self._get_siblings(concept_id)
        papers = self._get_papers(concept_id, limit=5)

        # 获取边缘节点（叶子节点）
        all_concepts = self.db.get_all_concepts()
        edge_nodes = []
        for c in all_concepts:
            children = self.db.get_concept_children(c['id'])
            if not children and c['id'] != concept_id:
                edge_nodes.append(c)

        # 构建 prompt（简化版）
        prompt = self._build_research_prompt(
            concept, ancestors, descendants, siblings, edge_nodes, papers
        )

        try:
            response = self.llm_client.generate(prompt)

            # 解析 JSON
            response_text = response.strip()
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                start_idx = 1
                end_idx = len(lines)
                if lines[-1].strip() == '```':
                    end_idx = len(lines) - 1
                response_text = '\n'.join(lines[start_idx:end_idx])

            return json.loads(response_text)

        except Exception as e:
            print(f"Research point discovery error: {e}")
            return []

    def _build_research_prompt(self, concept, ancestors, descendants, siblings, edge_nodes, papers):
        """构建研究点发现提示词"""
        return f"""<s>
你是科研导师，擅长从知识图谱结构中发现研究机会。

四种方法论：
- **空白地带法**：图谱中两个本应有联系的分支之间缺少连接
- **末端延伸法**：叶子节点代表最具体的技术，能否应用到其他分支
- **瓶颈识别法**：某节点连接大量子节点但自身缺少兄弟节点
- **迁移应用法**：一个分支的成熟方法能否迁移到另一个问题尚未解决的分支
</s>

<concept>
名称：{concept['text']}
层级：{concept.get('category', 'unknown')}
关联论文数：{concept.get('paper_count', 0)}
</concept>

<structure>
上游路径：{json.dumps([a.get('text') for a in ancestors], ensure_ascii=False)}
下游分支：{json.dumps([d.get('text') for d in descendants[:5]], ensure_ascii=False)}
邻域节点：{json.dumps([s.get('text') for s in siblings[:5]], ensure_ascii=False)}
</structure>

<task>
基于以上信息，发现 3 个有价值的研究方向。
</task>

<output_format>
返回 JSON 数组：
[
  {{
    "title": "研究点标题（15字以内）",
    "hypothesis": "核心假设",
    "description": "详细描述（80字以内）",
    "discovery_method": "gap_filling | leaf_extension | bottleneck | transfer",
    "rationale": "为什么图谱结构暗示了这个研究机会",
    "difficulty": "low | medium | high",
    "novelty": "incremental | moderate | high"
  }}
]
</output_format>
"""

    def answer_followup(self, question: str, concept_name: str, research_points: List[Dict]) -> str:
        """回答追问"""
        concept = self.db.get_concept_by_name(concept_name) or {}
        prompt = RESEARCH_POINT_FOLLOWUP_PROMPT.format(
            concept_name=concept_name,
            question=question,
            research_points=json.dumps([rp.get('title') for rp in research_points], ensure_ascii=False),
            category=concept.get('category', 'unknown'),
            paper_count=concept.get('paper_count', 0),
        )

        try:
            return self.llm_client.generate(prompt)
        except Exception as e:
            return f"回答生成失败: {str(e)}"

    def format_response(self, analysis: Dict[str, Any]) -> str:
        """格式化分析结果"""
        if 'error' in analysis:
            return analysis['error']

        concept = analysis.get('concept', {})
        structure = analysis.get('structure', {})
        research_points = analysis.get('research_points', [])
        s2_context = analysis.get('s2_context', '')

        lines = [
            f"**{concept.get('name', '概念')}**",
            f"层级：{concept.get('category', '?')} | 论文数：{concept.get('paper_count', 0)}",
            "",
        ]

        # 图谱结构
        if structure.get('ancestors'):
            lines.append("上游路径")
            lines.append(" -> ".join([a.get('text', '') for a in structure['ancestors'][:3]]))
            lines.append("")

        # S2 热度
        if s2_context:
            lines.append(f"领域热度：{s2_context}")
            lines.append("")

        # 研究点
        if research_points:
            lines.append("研究点建议")
            for i, rp in enumerate(research_points[:3], 1):
                difficulty_emoji = {'low': 'Low', 'medium': 'Medium', 'high': 'High'}.get(rp.get('difficulty'), 'Unknown')
                lines.append(f"{i}. **{rp.get('title', '')}** [{difficulty_emoji}]")
                lines.append(f"   {rp.get('description', '')}")
            lines.append("")

        lines.append("你可以继续追问某个研究点的具体内容")

        return '\n'.join(lines)