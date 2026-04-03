# mkg/agent/deep_research_agent.py
"""
Deep Research Agent - 多维度深入研究
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime


class SubAgent:
    """子代理 - 负责单一维度的研究"""

    def __init__(self, dimension: str, llm_client, db, s2_client=None):
        self.dimension = dimension
        self.llm_client = llm_client
        self.db = db
        self.s2_client = s2_client

    async def research(self, target: Dict[str, Any], context: str) -> Dict[str, Any]:
        """
        执行单一维度研究

        Args:
            target: 研究目标（概念或论文）
            context: 已有上下文

        Returns:
            研究发现
        """
        # 构建 ReAct prompt
        prompt = self._build_react_prompt(target, context)

        # 执行 ReAct 循环（最多 3 步）
        findings = await self._react_loop(prompt, max_steps=3)

        return {
            'dimension': self.dimension,
            'findings': findings,
            'confidence': self._calculate_confidence(findings),
        }

    def _build_react_prompt(self, target: Dict, context: str) -> str:
        """构建 ReAct 循环提示词"""
        return f"""<s>
你是研究助理，专注于「{self.dimension}」维度的分析。

目标对象：{target.get('name')} ({target.get('type')})
已有上下文：{context}
</s>

<react_pattern>
按照以下格式思考和行动：
Thought: 思考下一步应该做什么
Action: 选择一个行动（search | analyze | synthesize）
Action_Input: 行动的输入
Observation: 行动的结果（由系统提供）
... (重复直到得出结论)
Final_Answer: 该维度的最终发现
</react_pattern>

<available_actions>
- search: 搜索相关论文或概念（需要关键词）
- analyze: 分析已有数据（需要具体对象）
- synthesize: 综合信息得出结论（需要待综合的内容）
</available_actions>

开始分析！先给出你的第一个 Thought。
"""

    async def _react_loop(self, prompt: str, max_steps: int = 3) -> List[Dict]:
        """执行 ReAct 循环"""
        findings = []
        current_prompt = prompt

        for step in range(max_steps):
            try:
                response = self.llm_client.generate(current_prompt)

                # 解析 Thought/Action/Action_Input
                action_data = self._parse_action(response)

                if action_data.get('final_answer'):
                    findings.append({
                        'type': 'conclusion',
                        'content': action_data['final_answer'],
                        'step': step,
                    })
                    break

                # 执行 Action
                observation = await self._execute_action(action_data)

                # 添加 Observation 到 prompt
                current_prompt = f"{current_prompt}\n\n{response}\nObservation: {observation}"

                findings.append({
                    'type': action_data.get('action', 'unknown'),
                    'content': observation,
                    'step': step,
                })

            except Exception as e:
                findings.append({
                    'type': 'error',
                    'content': str(e),
                    'step': step,
                })
                break

        return findings

    def _parse_action(self, response: str) -> Dict:
        """解析 LLM 响应中的 Action"""
        result = {}

        lines = response.strip().split('\n')
        for line in lines:
            if line.startswith('Action:'):
                result['action'] = line.replace('Action:', '').strip()
            elif line.startswith('Action_Input:'):
                result['action_input'] = line.replace('Action_Input:', '').strip()
            elif line.startswith('Final_Answer:'):
                result['final_answer'] = line.replace('Final_Answer:', '').strip()

        return result

    async def _execute_action(self, action_data: Dict) -> str:
        """执行具体行动"""
        action = action_data.get('action', '')
        input_data = action_data.get('action_input', '')

        if action == 'search':
            return await self._search(input_data)
        elif action == 'analyze':
            return await self._analyze(input_data)
        elif action == 'synthesize':
            return self._synthesize(input_data)

        return f"未知行动: {action}"

    async def _search(self, query: str) -> str:
        """搜索相关内容"""
        if not self.s2_client:
            return "S2 API 未配置"

        try:
            results = self.s2_client.search_papers(query, limit=5)
            if not results:
                return "未找到相关论文"

            papers = []
            for p in results[:5]:
                papers.append(f"- {p.get('title')} ({p.get('year')}) - {p.get('citationCount')} 引用")
            return "相关论文:\n" + "\n".join(papers)
        except Exception as e:
            return f"搜索失败: {str(e)}"

    async def _analyze(self, target_name: str) -> str:
        """分析概念或论文（模糊匹配）"""
        # 尝试从数据库获取概念（模糊匹配）
        concepts = self.db.get_all_concepts()
        target_lower = target_name.lower()

        matched = None
        # 精确匹配
        for c in concepts:
            if c['text'].lower() == target_lower:
                matched = c
                break

        # 模糊匹配
        if not matched:
            for c in concepts:
                if target_lower in c['text'].lower() or c['text'].lower() in target_lower:
                    matched = c
                    break

        if matched:
            # 获取结构信息
            ancestors = self.db.get_concept_parents(matched['id'])
            children = self.db.get_concept_children(matched['id'])
            papers = self.db.get_papers_by_concept(matched['id'])
            return f"概念: {matched['text']}\n上级: {len(ancestors)} 个\n下级: {len(children)} 个\n论文数: {matched.get('paper_count', 0)}\n相关论文: {len(papers)} 篇"

        return f"未找到概念: {target_name}"

    def _synthesize(self, content: str) -> str:
        """综合信息"""
        prompt = f"综合以下信息，给出简洁结论:\n{content}"
        try:
            return self.llm_client.generate(prompt)
        except Exception as e:
            return f"综合失败: {str(e)}"

    def _calculate_confidence(self, findings: List[Dict]) -> float:
        """计算置信度"""
        if not findings:
            return 0.0

        # 基于是否有结论和错误计算
        has_conclusion = any(f['type'] == 'conclusion' for f in findings)
        has_error = any(f['type'] == 'error' for f in findings)

        if has_error:
            return 0.3
        if has_conclusion:
            return 0.85

        return 0.6


class DeepResearchAgent:
    """深入研究 Agent - 协调多维度研究"""

    DEFAULT_DIMENSIONS = [
        '理论基础',
        '应用场景',
        '技术演进',
        '研究前沿',
        '潜在挑战',
    ]

    def __init__(self, llm_client, db, s2_client=None):
        self.llm_client = llm_client
        self.db = db
        self.s2_client = s2_client

    def start_research(self, target_type: str, target_id: str,
                       target_name: str, query: str,
                       dimensions: Optional[List[str]] = None) -> str:
        """
        启动深入研究

        Returns:
            session_id: 研究会话 ID
        """
        session_id = str(uuid.uuid4())
        dims = dimensions or self.DEFAULT_DIMENSIONS

        # 创建会话
        self.db.create_research_session(
            session_id, target_type, target_id, target_name, query, dims
        )

        # 异步启动研究任务
        asyncio.create_task(self._run_research(session_id))

        return session_id

    async def _run_research(self, session_id: str) -> None:
        """执行多维度研究"""
        session = self.db.get_research_session(session_id)
        if not session:
            return

        target = {
            'type': session['target_type'],
            'id': session['target_id'],
            'name': session['target_name'],
        }

        dimensions = json.loads(session['dimensions']) if session['dimensions'] else self.DEFAULT_DIMENSIONS
        completed = []
        total = len(dimensions)

        # 逐维度执行
        for i, dim in enumerate(dimensions):
            try:
                # 创建子代理
                sub_agent = SubAgent(dim, self.llm_client, self.db, self.s2_client)

                # 执行研究
                result = await sub_agent.research(target, session.get('query', ''))

                # 保存发现
                self.db.save_research_finding(
                    session_id, dim,
                    result.get('findings', [])[-1].get('type', 'unknown') if result.get('findings') else 'unknown',
                    json.dumps(result.get('findings', []), ensure_ascii=False),
                    [], result.get('confidence', 0.5)
                )

                completed.append(dim)
                progress = int((i + 1) / total * 100)
                self.db.update_research_progress(session_id, progress, completed)

            except Exception as e:
                print(f"Dimension {dim} failed: {e}")
                completed.append(dim)

        # 生成报告
        report = self._generate_report(session_id)
        self.db.save_research_report(session_id, report)

    def _generate_report(self, session_id: str) -> str:
        """生成研究报告"""
        session = self.db.get_research_session(session_id)
        findings = self.db.get_research_findings(session_id)

        lines = [
            f"# {session['target_name']} 深入研究报告",
            f"",
            f"**研究时间**: {session['started_at']}",
            f"**研究维度**: {session['dimensions']}",
            f"",
        ]

        for f in findings:
            lines.append(f"## {f['dimension']}")
            lines.append(f"")
            content = f['content']
            if isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    for item in parsed:
                        if isinstance(item, dict):
                            lines.append(f"**{item.get('type', 'Step')}**: {item.get('content', '')}")
                        else:
                            lines.append(str(item))
                except:
                    lines.append(content)
            else:
                lines.append(str(content))
            lines.append(f"置信度: {f['confidence']}")
            lines.append(f"")

        lines.append("---")
        lines.append("报告生成完毕")

        return "\n".join(lines)

    def get_status(self, session_id: str) -> Dict[str, Any]:
        """获取研究状态"""
        session = self.db.get_research_session(session_id)
        if not session:
            return {'error': 'Session not found'}

        dimensions = json.loads(session['dimensions']) if session['dimensions'] else []
        completed = json.loads(session['completed_dimensions']) if session['completed_dimensions'] else []

        return {
            'status': session['status'],
            'progress': session['progress'] or 0,
            'dimensions': dimensions,
            'completedDimensions': completed,
        }

    def get_report(self, session_id: str) -> Dict[str, Any]:
        """获取研究报告"""
        session = self.db.get_research_session(session_id)
        if not session:
            return {'error': 'Session not found'}

        return {
            'report': session['report'] or '研究进行中...',
            'format': 'markdown',
        }