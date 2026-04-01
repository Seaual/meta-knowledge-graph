# mkg/agent/lead_agent.py
import json
from typing import Optional, Dict, Any
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

    def recognize_intent(self, message: str, context: Dict[str, Any]) -> IntentResult:
        """
        识别用户意图

        Args:
            message: 用户消息
            context: 上下文摘要

        Returns:
            IntentResult: 意图识别结果
        """
        # 构建上下文信息
        current_target = "无"
        if context.get('currentTarget'):
            ct = context['currentTarget']
            current_target = f"{ct.get('type')}: {ct.get('name')}"

        key_findings = "无"
        if context.get('keyFindings'):
            key_findings = "; ".join(context['keyFindings'][:3])

        # 构建提示词
        prompt = LEAD_AGENT_INTENT_PROMPT.format(
            message=message,
            current_target=current_target,
            key_findings=key_findings
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
            return IntentResult.from_dict(result)

        except Exception as e:
            # 解析失败，返回默认意图
            return IntentResult(
                intent='lead',
                target_type=None,
                target_name=None,
                confidence=0.0,
                reasoning=f"意图识别失败: {str(e)}"
            )

    def generate_response(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成响应（Lead Agent 的通用对话能力）

        Args:
            message: 用户消息
            context: 上下文摘要

        Returns:
            响应字典
        """
        intent = self.recognize_intent(message, context)

        # 如果是 lead 意图，生成通用响应
        if intent.intent == 'lead':
            response = self._generate_lead_response(message, context, intent)
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
                                 intent: IntentResult) -> str:
        """生成 Lead Agent 的通用响应"""
        prompt = f"""用户说：{message}

意图分析结果：
- 意图：{intent.intent}
- 目标：{intent.target_name or '未指定'}
- 置信度：{intent.confidence}

请以友好、简洁的方式回复用户（不超过100字）。如果用户想使用特定功能但表述不清，可以引导他们更清楚地说明。"""

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