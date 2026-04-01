# Research Agent Phase 2: Citation Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Citation Agent that analyzes paper citations and references using S2 API, providing statistics and deep analysis.

**Architecture:** Citation Agent receives paper identifiers from Lead Agent, queries S2 API for citation data, performs statistical analysis, and returns structured results. It integrates with existing S2Client and adds analysis capabilities.

**Tech Stack:** Python, FastAPI, Semantic Scholar API, LiteLLM

---

## File Structure

```
mkg/agent/
├── citation_agent.py      # Citation Agent implementation
└── prompts.py             # Add citation analysis prompts

backend/routes/
└── agent.py               # Modify to dispatch to Citation Agent
```

---

### Task 1: Add Citation Analysis Prompts

**Files:**
- Modify: `mkg/agent/prompts.py`

- [ ] **Step 1: Add citation analysis prompts**

Add these to `mkg/agent/prompts.py`:

```python
CITATION_ANALYSIS_PROMPT = """<s>
你是一位学术引用分析专家。你需要分析论文的引用关系，提供深度洞察。

分析维度：
1. **引用统计** - 被引次数、年份分布、领域分布
2. **高影响力引用者** - 识别引用该论文的高影响力工作
3. **引用脉络演变** - 追踪引用如何随时间演变
4. **引用聚类** - 识别引用该论文的主要研究方向
</s>

<paper>
标题：{title}
被引次数：{citation_count}
发表年份：{year}
</paper>

<citation_data>
{citation_data}
</citation_data>

<task>
基于以上数据，生成引用分析报告。
</task>

<output_format>
返回 JSON：
{
  "summary": "一句话总结该论文的引用影响力",
  "statistics": {
    "total_citations": 数字,
    "recent_citations_3y": 近3年引用数,
    "avg_citations_per_year": 年均引用
  },
  "field_distribution": [
    {{"field": "领域名", "count": 数量, "percentage": 百分比}}
  ],
  "top_citers": [
    {{"title": "论文标题", "citations": 该论文被引数, "year": 年份, "venue": 期刊/会议"}}
  ],
  "citation_trend": {{
    "trend": "rising | stable | declining",
    "peak_year": 引用峰值年份,
    "analysis": "趋势分析（50字以内）"
  }},
  "research_clusters": [
    {{"cluster": "研究聚类名称", "description": "简要描述", "key_papers": 数量}}
  ],
  "insights": "关键洞察（100字以内）"
}
</output_format>
"""
```

- [ ] **Step 2: Commit**

```bash
git add mkg/agent/prompts.py
git commit -m "feat: add citation analysis prompts for Citation Agent"
```

---

### Task 2: Create Citation Agent

**Files:**
- Create: `mkg/agent/citation_agent.py`

- [ ] **Step 1: Create Citation Agent**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add mkg/agent/citation_agent.py
git commit -m "feat: add Citation Agent for paper citation analysis"
```

---

### Task 3: Update Lead Agent to Dispatch to Citation Agent

**Files:**
- Modify: `mkg/agent/lead_agent.py`
- Modify: `mkg/agent/__init__.py`

- [ ] **Step 1: Update __init__.py**

```python
# mkg/agent/__init__.py
from .lead_agent import LeadAgent
from .citation_agent import CitationAgent

__all__ = ['LeadAgent', 'CitationAgent']
```

- [ ] **Step 2: Add dispatch logic to lead_agent.py**

Add this method to the `LeadAgent` class in `mkg/agent/lead_agent.py`:

```python
    def dispatch_to_citation_agent(self, target_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """分发到 Citation Agent"""
        from .citation_agent import CitationAgent
        from mkg.semantic_scholar import S2Client

        # 创建 S2 客户端
        s2_client = S2Client()

        # 创建 Citation Agent
        citation_agent = CitationAgent(self.llm_client, s2_client)

        # 执行分析
        result = citation_agent.analyze(target_name, identifier_type='title')

        # 格式化响应
        if 'error' in result:
            return {
                'message': result['error'],
                'agent': 'citation',
                'contextUpdate': None
            }

        formatted = citation_agent.format_response(result)

        return {
            'message': formatted,
            'agent': 'citation',
            'contextUpdate': {
                'currentTarget': {
                    'type': 'paper',
                    'id': result.get('paper', {}).get('title', ''),
                    'name': result.get('paper', {}).get('title', ''),
                },
                'keyFindings': [result.get('analysis', {}).get('summary', '')],
            }
        }
```

- [ ] **Step 3: Commit**

```bash
git add mkg/agent/__init__.py mkg/agent/lead_agent.py
git commit -m "feat: add Citation Agent dispatch to Lead Agent"
```

---

### Task 4: Update Agent API Route

**Files:**
- Modify: `backend/routes/agent.py`

- [ ] **Step 1: Add Citation Agent handling**

Modify the `chat` function in `backend/routes/agent.py` to handle citation intent:

```python
@router.post("/chat", response_model=AgentChatResponse)
def chat(request: AgentChatRequest):
    """
    处理用户对话

    1. Lead Agent 识别意图
    2. 根据意图分发到专业 Agent
    3. 返回响应
    """
    lead_agent = get_lead_agent()

    if not lead_agent:
        raise HTTPException(
            status_code=500,
            detail="LLM 未配置，请先在设置中配置 API Key"
        )

    # 识别意图并生成响应
    context_dict = request.context.model_dump()
    result = lead_agent.generate_response(request.message, context_dict)

    # 如果有意图结果，表示需要分发到专业 Agent
    if 'intent_result' in result:
        intent_result = result['intent_result']
        intent = intent_result['intent']
        target_name = intent_result.get('target_name')

        # 分发到 Citation Agent
        if intent == 'citation' and target_name:
            citation_result = lead_agent.dispatch_to_citation_agent(target_name, context_dict)
            return AgentChatResponse(
                message=citation_result['message'],
                agent=citation_result['agent'],
                contextUpdate=citation_result.get('contextUpdate')
            )

        # 其他 Agent 待实现
        return AgentChatResponse(
            message=f"我理解您想要{intent_result['reasoning']}。该功能即将上线！",
            agent=intent_result['intent'],
            contextUpdate=None
        )

    return AgentChatResponse(
        message=result['message'],
        agent=result['agent'],
        contextUpdate=result.get('contextUpdate')
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/routes/agent.py
git commit -m "feat: integrate Citation Agent into chat endpoint"
```

---

### Task 5: Test Citation Agent

**Files:**
- No new files

- [ ] **Step 1: Start backend server**

```bash
cd D:/meta-knowledge-graph-main
python -m uvicorn backend.main:app --port 8088 --reload
```

- [ ] **Step 2: Test with curl**

```bash
curl -X POST http://localhost:8088/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "分析 Transformer 论文的引用关系", "context": {"contextTags": [], "keyFindings": [], "intentHistory": [], "lastActiveAgent": "lead"}}'
```

Expected: JSON response with citation analysis

- [ ] **Step 3: Test in browser**

1. Open http://localhost:5173
2. Click the bubble to open dialog
3. Send: "分析 Attention Is All You Need 这篇论文的引用"
4. Verify citation analysis is returned

---

## Summary

Phase 2 delivers:
- ✅ Citation Agent with S2 API integration
- ✅ Citation statistics (total, yearly, field distribution)
- ✅ High-impact citers identification
- ✅ Citation trend analysis
- ✅ Research clustering
- ✅ Integration with Lead Agent dispatch