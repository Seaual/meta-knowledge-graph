# mkg/agent/citation_agent.py
"""
Citation Agent - 分析论文引用关系
"""

import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from .prompts import CITATION_ANALYSIS_PROMPT


@dataclass
class CitationStats:
    """引用统计"""
    total_citations: int
    recent_citations_3y: int
    avg_citations_per_year: float


@dataclass
class FieldDistribution:
    """领域分布"""
    field: str
    count: int
    percentage: float


@dataclass
class TopCiter:
    """高影响力引用者"""
    title: str
    citations: int
    year: int
    venue: str


@dataclass
class CitationTrend:
    """引用趋势"""
    trend: str  # rising | stable | declining
    peak_year: int
    analysis: str


@dataclass
class ResearchCluster:
    """研究聚类"""
    cluster: str
    description: str
    key_papers: int


@dataclass
class CitationAnalysisResult:
    """引用分析结果"""
    summary: str
    statistics: CitationStats
    field_distribution: List[FieldDistribution]
    top_citers: List[TopCiter]
    citation_trend: CitationTrend
    research_clusters: List[ResearchCluster]
    insights: str


class CitationAgent:
    """引用分析 Agent"""

    def __init__(self, llm_client, s2_client):
        """
        初始化 Citation Agent

        Args:
            llm_client: LLM 客户端
            s2_client: S2 API 客户端
        """
        self.llm_client = llm_client
        self.s2_client = s2_client

    def analyze(self, paper_identifier: str, identifier_type: str = 'doi') -> Dict[str, Any]:
        """
        分析论文引用

        Args:
            paper_identifier: 论文标识（DOI 或标题）
            identifier_type: 标识类型 ('doi' 或 'title')

        Returns:
            分析结果字典
        """
        # 1. 获取论文详情
        paper = self._get_paper(paper_identifier, identifier_type)
        if not paper:
            return {'error': f'无法找到论文: {paper_identifier}'}

        # 2. 获取引用数据
        citations = self._get_citations(paper['paperId'])
        references = self._get_references(paper['paperId'])

        # 3. 分析引用数据
        citation_data = self._prepare_citation_data(paper, citations, references)

        # 4. LLM 深度分析
        analysis = self._analyze_with_llm(paper, citation_data)

        return {
            'paper': {
                'title': paper.get('title'),
                'year': paper.get('year'),
                'citation_count': paper.get('citationCount', 0),
                'venue': paper.get('venue'),
            },
            'analysis': analysis,
            'raw_citations_count': len(citations),
            'raw_references_count': len(references),
        }

    def _get_paper(self, identifier: str, identifier_type: str) -> Optional[Dict]:
        """获取论文信息"""
        try:
            if identifier_type == 'doi':
                return self.s2_client.get_paper_details(f"DOI:{identifier}")
            else:
                return self.s2_client.match_paper_by_title(identifier)
        except Exception as e:
            print(f"Error getting paper: {e}")
            return None

    def _get_citations(self, paper_id: str, limit: int = 100) -> List[Dict]:
        """获取引用该论文的论文列表"""
        try:
            return self.s2_client.get_paper_citations(paper_id, limit=limit)
        except Exception as e:
            print(f"Error getting citations: {e}")
            return []

    def _get_references(self, paper_id: str, limit: int = 50) -> List[Dict]:
        """获取该论文引用的论文列表"""
        try:
            return self.s2_client.get_paper_references(paper_id, limit=limit)
        except Exception as e:
            print(f"Error getting references: {e}")
            return []

    def _prepare_citation_data(self, paper: Dict, citations: List[Dict], references: List[Dict]) -> str:
        """准备引用数据用于 LLM 分析"""
        # 统计年份分布
        year_dist = {}
        for c in citations:
            year = c.get('year', 0)
            if year > 0:
                year_dist[year] = year_dist.get(year, 0) + 1

        # 统计领域分布（基于引用者的 venue）
        venue_dist = {}
        for c in citations:
            venue = c.get('venue') or 'Unknown'
            venue_dist[venue] = venue_dist.get(venue, 0) + 1

        # 排序获取 Top venues
        top_venues = sorted(venue_dist.items(), key=lambda x: x[1], reverse=True)[:10]

        # 高影响力引用者
        top_citers = sorted(citations, key=lambda x: x.get('citationCount', 0), reverse=True)[:10]

        data = {
            'total_citations': len(citations),
            'year_distribution': dict(sorted(year_dist.items())),
            'venue_distribution': dict(top_venues),
            'top_citers': [
                {
                    'title': c.get('title'),
                    'citations': c.get('citationCount', 0),
                    'year': c.get('year'),
                    'venue': c.get('venue'),
                }
                for c in top_citers if c.get('title')
            ],
            'references_count': len(references),
        }

        return json.dumps(data, ensure_ascii=False, indent=2)

    def _analyze_with_llm(self, paper: Dict, citation_data: str) -> Dict[str, Any]:
        """使用 LLM 进行深度分析"""
        prompt = CITATION_ANALYSIS_PROMPT.format(
            title=paper.get('title', 'Unknown'),
            citation_count=paper.get('citationCount', 0),
            year=paper.get('year', 'Unknown'),
            citation_data=citation_data,
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
            print(f"LLM analysis error: {e}")
            return {
                'summary': f"该论文被引用 {paper.get('citationCount', 0)} 次",
                'statistics': {
                    'total_citations': paper.get('citationCount', 0),
                    'recent_citations_3y': 0,
                    'avg_citations_per_year': 0,
                },
                'field_distribution': [],
                'top_citers': [],
                'citation_trend': {'trend': 'unknown', 'peak_year': 0, 'analysis': ''},
                'research_clusters': [],
                'insights': '分析失败，请稍后重试',
            }

    def format_response(self, analysis: Dict[str, Any]) -> str:
        """格式化分析结果为用户友好的文本"""
        if 'error' in analysis:
            return analysis['error']

        paper = analysis.get('paper', {})
        result = analysis.get('analysis', {})

        lines = [
            f"**{paper.get('title', '论文')}**",
            f"发表：{paper.get('year', '?')} | {paper.get('venue', '?')}",
            "",
            f"📊 **引用统计**",
            f"- 总被引次数：{result.get('statistics', {}).get('total_citations', 0)}",
            f"- 近3年引用：{result.get('statistics', {}).get('recent_citations_3y', 0)}",
            "",
        ]

        # 领域分布
        field_dist = result.get('field_distribution', [])
        if field_dist:
            lines.append("🎯 **主要引用领域**")
            for f in field_dist[:5]:
                lines.append(f"- {f.get('field')}: {f.get('percentage', 0):.1f}%")
            lines.append("")

        # 引用趋势
        trend = result.get('citation_trend', {})
        if trend:
            trend_emoji = {'rising': '📈', 'stable': '➡️', 'declining': '📉'}.get(trend.get('trend'), '📊')
            lines.append(f"{trend_emoji} **引用趋势**")
            lines.append(f"- {trend.get('analysis', '')}")
            lines.append("")

        # 关键洞察
        lines.append(f"💡 **{result.get('insights', '')}**")

        return '\n'.join(lines)