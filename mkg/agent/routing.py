# mkg/agent/routing.py
"""
意图路由 - 使用 LLM 自动理解用户意图并路由到正确的 agent
"""

from typing import Optional, Tuple, Dict, Any
import json


# ============================================================
# Agent 类型定义
# ============================================================

AGENT_TYPES = {
    "lead": "通用助手 - 处理一般对话、问候、帮助请求",
    "citation": "引用分析 - 分析论文的引用关系、被引用情况",
    "research": "研究点分析 - 分析概念的研究方向、研究机会、概念图谱",
    "deep_research": "深入研究 - 对某个主题进行全面系统的研究",
    "paper_qa": "论文问答 - 回答关于特定论文内容的问题",
    "move_paper": "文件管理 - 移动论文到文件夹、创建文件夹",
}


# ============================================================
# LLM 路由 Prompt
# ============================================================

ROUTING_PROMPT = """你是一个意图识别系统。分析用户消息，判断用户想要做什么，然后路由到正确的 agent。

## 可用的 Agent 类型：
{agent_descriptions}

## 当前上下文：
- 当前目标: {current_target}
- 上传的论文: {uploaded_papers}

## 用户消息：
{message}

## 任务：
1. 分析用户意图
2. 选择最合适的 agent 类型
3. 如果用户提到了特定的论文或概念，提取目标名称

请以 JSON 格式返回（只返回 JSON，不要其他内容）：
{{
    "intent": "<agent类型>",
    "target_name": "<目标名称或null>",
    "reasoning": "<简短的理由>"
}}
"""


# ============================================================
# 路由函数
# ============================================================

def route_intent(message: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, Optional[str]]:
    """
    智能意图路由：LLM 优先，关键词兜底

    Args:
        message: 用户消息
        context: 当前上下文（包含 currentTarget 等）

    Returns:
        (intent, target_name) - 意图和目标名称
    """
    if context is None:
        context = {}

    # 1. 先尝试 LLM 路由（智能）
    try:
        llm_intent, llm_target = llm_route_intent(message, context)
        if llm_intent != "lead":
            return llm_intent, llm_target
    except Exception as e:
        print(f"LLM routing failed: {e}")

    # 2. LLM 路由失败或返回 lead，尝试关键词路由
    intent, target_name = keyword_route_intent(message, context)

    # 3. 返回结果
    return intent, target_name


def llm_route_intent(message: str, context: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """
    使用 LLM 进行智能意图路由
    """
    import requests
    import json
    from mkg.database import Database
    from pathlib import Path

    # 获取 LLM 配置
    db_path = Path(__file__).parent.parent.parent / "mkg.db"
    db = Database(str(db_path))
    db.connect()

    config = db.get_llm_config()
    if not config or not config.get('providers'):
        raise ValueError("LLM 未配置")

    provider_config = db.get_active_llm_provider()
    if not provider_config:
        provider_config = config['providers'][0]

    provider = provider_config.get('provider', 'openai')
    api_key = provider_config.get('api_key')
    model = provider_config.get('model', 'gpt-4o-mini')
    base_url = provider_config.get('base_url')

    # 构建 agent 描述
    agent_descriptions = "\n".join([
        f"- {name}: {desc}" for name, desc in AGENT_TYPES.items()
    ])

    # 构建上下文信息
    current_target = context.get("currentTarget")
    target_info = "无"
    if current_target:
        target_info = f"{current_target.get('type')}: {current_target.get('name')}"

    uploaded_papers = context.get("uploadedPapers", [])
    papers_info = "无"
    if uploaded_papers:
        papers_info = ", ".join([p.get("title", "") for p in uploaded_papers[-3:]])

    # 构建 prompt
    prompt = ROUTING_PROMPT.format(
        agent_descriptions=agent_descriptions,
        current_target=target_info,
        uploaded_papers=papers_info,
        message=message
    )

    # 直接使用 HTTP 请求调用 API
    # 判断是 OpenAI 格式还是 Anthropic 格式
    if base_url and 'anthropic' in base_url.lower():
        # Anthropic 格式
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}]
        }
        endpoint = base_url.rstrip('/') + "/v1/messages"
    else:
        # OpenAI 格式
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}]
        }
        endpoint = base_url.rstrip('/') + "/chat/completions" if base_url else "https://api.openai.com/v1/chat/completions"

    response = requests.post(endpoint, headers=headers, json=data, timeout=60)
    response.raise_for_status()
    result = response.json()

    # 解析响应
    if 'content' in result:
        # Anthropic 格式
        content_list = result['content']
        if isinstance(content_list, list) and len(content_list) > 0:
            content = content_list[0].get('text', '') or content_list[0].get('content', '')
        else:
            content = str(content_list)
    elif 'choices' in result:
        # OpenAI 格式
        content = result['choices'][0]['message']['content']
    else:
        # 未知格式，尝试提取
        content = str(result)

    # 解析 JSON
    try:
        # 尝试找到 JSON 块
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        parsed = json.loads(content.strip())
        intent = parsed.get("intent", "lead")
        target_name = parsed.get("target_name")

        # 验证 intent 是否有效
        if intent not in AGENT_TYPES:
            intent = "lead"

        return intent, target_name

    except json.JSONDecodeError:
        # JSON 解析失败，返回默认
        return "lead", None


# ============================================================
# 关键词路由（作为后备）
# ============================================================

ROUTING_RULES: Dict[str, list] = {
    "citation": [
        "引用", "被引", "citation", "谁引用了", "引用了谁",
        "引用关系", "引用分析", "被谁引用"
    ],
    "research": [
        "研究点", "研究方向", "研究机会", "概念分析",
        "有什么研究", "可以研究什么", "研究价值",
        "研究热点", "领域热点", "可以研究的", "研究什么",
        "深入分析", "分析概念", "概念的研究",
        "研究建议", "拓展研究", "拓展", "研究拓展", "未来研究",
    ],
    "deep_research": [
        "深入研究", "系统分析", "详细研究", "全面分析",
        "帮我研究", "完整研究", "综合研究"
    ],
    "paper_qa": [
        "这篇论文讲了什么", "论文内容", "论文创新点", "创新点",
        "论文摘要", "这篇论文是什么", "论文讲了啥",
        "论文主要", "论文的贡献", "论文方法", "论文结论",
        "论文实验", "这篇论文", "论文介绍", "论文概述",
        "方法是什么", "结论是什么", "创新点是什么", "实验结果",
        "论文是什么", "这论文", "论文的", "这篇文章",
        "论文讲", "论文什么", "论文内容是什么"
    ],
    "move_paper": [
        "移动到", "放到", "新建文件夹", "把论文放到",
        "移到", "转移到", "放入", "归类到",
        "新建一个文件夹", "创建文件夹", "整理"
    ],
}

INTENT_PRIORITY = ["citation", "research", "deep_research", "paper_qa", "move_paper"]

PRONOUN_PATTERNS = [
    "这篇论文", "这篇文章", "这个论文", "这篇",
    "这个概念", "这个节点", "这个主题",
    "刚才上传的论文", "上传的论文", "刚才的论文"
]


def keyword_route_intent(message: str, context: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """
    基于关键词的后备路由
    """
    message_lower = message.lower()

    # 按优先级匹配关键词
    for intent in INTENT_PRIORITY:
        keywords = ROUTING_RULES.get(intent, [])
        if any(kw in message_lower for kw in keywords):
            target_name = extract_target(message, context)
            return intent, target_name

    return "lead", None


def extract_target(message: str, context: Dict[str, Any]) -> Optional[str]:
    """从消息或上下文提取目标名称"""
    has_pronoun = any(p in message for p in PRONOUN_PATTERNS)

    if has_pronoun:
        current_target = context.get("currentTarget")
        if current_target:
            return current_target.get("name")

    uploaded_papers = context.get("uploadedPapers", [])
    if uploaded_papers and any(p in message for p in ["刚才上传", "上传的论文"]):
        return uploaded_papers[-1].get("title")

    return None


def needs_summary(intent: str, response_length: int = 0) -> bool:
    """判断是否需要 Lead Agent 汇总"""
    if intent == "deep_research":
        return True
    if response_length > 1000:
        return True
    return False


def get_intent_keywords(intent: str) -> list:
    """获取某个意图的触发关键词"""
    return ROUTING_RULES.get(intent, [])


def add_intent_keyword(intent: str, keyword: str):
    """添加新的触发关键词"""
    if intent not in ROUTING_RULES:
        ROUTING_RULES[intent] = []
    if keyword not in ROUTING_RULES[intent]:
        ROUTING_RULES[intent].append(keyword)