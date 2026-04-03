# mkg/agent/lead_agent.py
import json
from typing import Optional, Dict, Any, List
from .prompts import LEAD_AGENT_SYSTEM_PROMPT, LEAD_AGENT_INTENT_PROMPT


class IntentResult:
    """意图识别结果"""
    def __init__(self, intent: str, target_type: Optional[str], target_name: Optional[str],
                 confidence: float, reasoning: str):
        self.intent = intent
        self.target_type = target_type
        self.target_name = target_name
        self.confidence = confidence
        self.reasoning = reasoning

    @classmethod
    def from_dict(cls, data: dict) -> 'IntentResult':
        return cls(
            intent=data.get('intent', 'lead'),
            target_type=data.get('target_type'),
            target_name=data.get('target_name'),
            confidence=data.get('confidence', 0.5),
            reasoning=data.get('reasoning', '')
        )


class LeadAgent:
    """Lead Agent - 意图识别和任务分发"""

    def __init__(self, llm_client, db=None):
        """
        初始化 Lead Agent

        Args:
            llm_client: LLM 客户端（LiteLLMClient 实例）
            db: Database 实例（可选）
        """
        self.llm_client = llm_client
        self.db = db

    def recognize_intent(self, message: str, context: Dict[str, Any], history: List[Dict] = None) -> IntentResult:
        """
        识别用户意图

        Args:
            message: 用户消息
            context: 上下文摘要
            history: 对话历史

        Returns:
            IntentResult: 意图识别结果
        """
        if history is None:
            history = []

        # 构建上下文信息
        current_target = "无"
        current_target_obj = context.get('currentTarget')
        if current_target_obj:
            ct = current_target_obj
            current_target = f"{ct.get('type')}: {ct.get('name')}"

        key_findings = "无"
        if context.get('keyFindings'):
            key_findings = "; ".join(context['keyFindings'][:3])

        # 构建对话历史摘要
        history_summary = ""
        if history:
            recent_history = history[-6:]  # 最近 6 条消息
            history_summary = "\n最近对话：\n" + "\n".join([
                f"- {m['role']}: {m['content'][:100]}..." if len(m['content']) > 100 else f"- {m['role']}: {m['content']}"
                for m in recent_history
            ])

        # 构建提示词
        prompt = LEAD_AGENT_INTENT_PROMPT.format(
            message=message,
            current_target=current_target,
            key_findings=key_findings,
            history_summary=history_summary
        )

        try:
            # 调用 LLM
            response = self.llm_client.generate(LEAD_AGENT_SYSTEM_PROMPT + "\n\n" + prompt)

            # 解析 JSON 响应
            # 处理可能的 markdown 代码块
            response_text = response.strip()
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                start_idx = 1
                end_idx = len(lines)
                if lines[-1].strip() == '```':
                    end_idx = len(lines) - 1
                response_text = '\n'.join(lines[start_idx:end_idx])

            result = json.loads(response_text)
            intent_result = IntentResult.from_dict(result)

            # 如果 target_name 是代词，从上下文中提取实际名称
            pronoun_patterns = ['这篇论文', '这篇文章', '这个论文', '这个概念', '这个节点', '这个主题', '刚才上传的论文', '上传的论文']
            if intent_result.target_name and intent_result.target_name.lower() in pronoun_patterns:
                if current_target_obj:
                    intent_result.target_name = current_target_obj.get('name')
                    intent_result.target_type = current_target_obj.get('type')

            # 如果 target_name 为 None 但上下文有目标，且意图是 citation/research/deep_research/paper_qa
            if intent_result.target_name is None and current_target_obj:
                if intent_result.intent in ['citation', 'research', 'deep_research', 'paper_qa']:
                    intent_result.target_name = current_target_obj.get('name')
                    intent_result.target_type = current_target_obj.get('type')

            return intent_result

        except Exception as e:
            # 解析失败，返回默认意图
            return IntentResult(
                intent='lead',
                target_type=None,
                target_name=None,
                confidence=0.0,
                reasoning=f"意图识别失败: {str(e)}"
            )

    def generate_response(self, message: str, context: Dict[str, Any], history: List[Dict] = None) -> Dict[str, Any]:
        """
        生成响应（Lead Agent 的通用对话能力）

        Args:
            message: 用户消息
            context: 上下文摘要
            history: 对话历史

        Returns:
            响应字典
        """
        if history is None:
            history = []

        intent = self.recognize_intent(message, context, history)

        # 如果是 lead 意图，生成通用响应
        if intent.intent == 'lead':
            response = self._generate_lead_response(message, context, intent, history)
            return {
                'message': response,
                'agent': 'lead',
                'contextUpdate': None
            }

        # 否则返回意图信息，由路由层分发
        return {
            'message': f"正在为您分析...",
            'agent': intent.intent,
            'intent_result': {
                'intent': intent.intent,
                'target_type': intent.target_type,
                'target_name': intent.target_name,
                'confidence': intent.confidence,
                'reasoning': intent.reasoning
            },
            'contextUpdate': None
        }

    def _generate_lead_response(self, message: str, context: Dict[str, Any],
                                 intent: IntentResult, history: List[Dict] = None) -> str:
        """生成 Lead Agent 的通用响应"""
        if history is None:
            history = []

        # 构建对话历史
        history_text = ""
        if history:
            recent_history = history[-6:]
            history_text = "\n\n对话历史：\n" + "\n".join([
                f"{m['role']}: {m['content']}"
                for m in recent_history
            ])

        prompt = f"""用户说：{message}
{history_text}

意图分析结果：
- 意图：{intent.intent}
- 目标：{intent.target_name or '未指定'}
- 置信度：{intent.confidence}

请以友好、简洁的方式回复用户（不超过100字）。参考对话历史，保持上下文连贯。如果用户想使用特定功能但表述不清，可以引导他们更清楚地说明。"""

        try:
            return self.llm_client.generate(prompt)
        except Exception:
            return "抱歉，我遇到了一些问题。请稍后重试。"

    def dispatch_to_citation_agent(self, target_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """分发到 Citation Agent"""
        from .citation_agent import CitationAgent
        from mkg.semantic_scholar import S2Client

        # 创建 S2 客户端
        s2_client = S2Client()

        # 创建 Citation Agent（传入数据库实例）
        citation_agent = CitationAgent(self.llm_client, s2_client, self.db)

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

    def dispatch_to_research_agent(self, target_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """分发到 Research Point Agent"""
        from .research_agent import ResearchPointAgent
        from mkg.semantic_scholar import S2Client

        # 创建 S2 客户端
        s2_client = S2Client()

        # 创建 Research Agent
        research_agent = ResearchPointAgent(self.llm_client, self.db, s2_client)

        # 执行分析
        result = research_agent.analyze(target_name)

        # 格式化响应
        if 'error' in result:
            return {
                'message': result['error'],
                'agent': 'research',
                'contextUpdate': None
            }

        formatted = research_agent.format_response(result)

        return {
            'message': formatted,
            'agent': 'research',
            'contextUpdate': {
                'currentTarget': {
                    'type': 'concept',
                    'id': result.get('concept', {}).get('id', ''),
                    'name': result.get('concept', {}).get('name', ''),
                },
            }
        }

    def dispatch_to_deep_research(self, target_name: str, target_type: str,
                                   target_id: str, query: str,
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """分发到 Deep Research Agent"""
        from .deep_research_agent import DeepResearchAgent
        from mkg.semantic_scholar import S2Client

        # 创建 S2 客户端
        s2_client = S2Client()

        # 创建 Deep Research Agent
        deep_agent = DeepResearchAgent(self.llm_client, self.db, s2_client)

        # 启动研究
        session_id = deep_agent.start_research(
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            query=query,
        )

        return {
            'message': f'已启动「{target_name}」的深入研究，预计需要 1-2 分钟...',
            'agent': 'deep_research',
            'researchSessionId': session_id,
            'contextUpdate': {
                'currentTarget': {
                    'type': target_type,
                    'id': target_id,
                    'name': target_name,
                },
            }
        }

    def dispatch_to_paper_qa_agent(self, paper_identifier: str, question: str,
                                    context: Dict[str, Any]) -> Dict[str, Any]:
        """分发到 Paper QA Agent"""
        from .paper_qa_agent import PaperQAAgent
        from mkg.pdf_parser import PDFParser

        # 创建 PDF Parser
        pdf_parser = PDFParser()

        # 创建 Paper QA Agent
        paper_qa_agent = PaperQAAgent(self.llm_client, self.db, pdf_parser)

        # 获取论文 DOI（可能是标题或 DOI）
        paper = self._find_paper(paper_identifier)
        if not paper:
            return {
                'message': f'未找到论文: {paper_identifier}',
                'agent': 'paper_qa',
                'contextUpdate': None
            }

        # 执行问答
        result = paper_qa_agent.answer(question, paper['doi'])

        if 'error' in result:
            return {
                'message': result['error'],
                'agent': 'paper_qa',
                'contextUpdate': None
            }

        formatted = paper_qa_agent.format_response(result)

        return {
            'message': formatted,
            'agent': 'paper_qa',
            'contextUpdate': {
                'currentTarget': {
                    'type': 'paper',
                    'id': paper['doi'],
                    'name': paper.get('title', paper_identifier),
                },
            }
        }

    def dispatch_to_move_paper(self, paper_identifier: str, target_folder: str,
                               create_folder: bool, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理论文移动请求"""
        # 获取论文
        paper = self._find_paper(paper_identifier)
        if not paper:
            return {
                'message': f'未找到论文: {paper_identifier}',
                'agent': 'lead',
                'contextUpdate': None
            }

        # 查找目标文件夹
        folders = self.db.get_all_folders()
        target = None
        for folder in folders:
            if folder['name'] == target_folder or folder['id'] == target_folder:
                target = folder
                break

        if not target and create_folder:
            # 创建新文件夹
            folder_id = self.db.create_folder({'name': target_folder})
            target = {'id': folder_id, 'name': target_folder}
        elif not target:
            return {
                'message': f'未找到文件夹「{target_folder}」。需要我新建一个吗？',
                'agent': 'lead',
                'contextUpdate': None
            }

        # 移动论文
        self.db.move_paper_to_folder(paper['doi'], target['id'])

        return {
            'message': f'已将论文《{paper.get("title", paper_identifier)}》移动到文件夹「{target["name"]}」',
            'agent': 'lead',
            'contextUpdate': None
        }

    def _find_paper(self, identifier: str) -> Optional[Dict]:
        """查找论文（通过 DOI 或标题）"""
        # 尝试作为 DOI 查找
        paper = self.db.get_paper(identifier)
        if paper:
            return paper

        # 尝试模糊匹配标题
        papers = self.db.get_papers_by_status('processed')
        papers.extend(self.db.get_papers_by_status('pending'))

        for p in papers:
            if identifier.lower() in (p.get('title') or '').lower():
                return p

        return None