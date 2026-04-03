# mkg/agent/routing.py
"""
意图路由规则 - 基于关键词的规则路由，无需 LLM 调用
"""

from typing import Optional, Tuple, Dict, Any


# ============================================================
# 路由规则定义
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
        # 概念图谱查询
        "看下我的图谱", "我的图谱", "图谱", "概念图谱",
        "概念图", "知识图谱", "查看图谱", "显示图谱",
        "这个概念", "关于概念", "概念是什么", "概念的",
        "概念点", "节点", "概念节点",
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

# 意图优先级（按顺序匹配）
INTENT_PRIORITY = ["citation", "research", "deep_research", "paper_qa", "move_paper"]

# 代词模式
PRONOUN_PATTERNS = [
    "这篇论文", "这篇文章", "这个论文", "这篇",
    "这个概念", "这个节点", "这个主题",
    "刚才上传的论文", "上传的论文", "刚才的论文"
]


# ============================================================
# 路由函数
# ============================================================

def route_intent(message: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, Optional[str]]:
    """
    基于规则的意图路由

    Args:
        message: 用户消息
        context: 当前上下文（包含 currentTarget 等）

    Returns:
        (intent, target_name) - 意图和目标名称
    """
    if context is None:
        context = {}

    message_lower = message.lower()

    # 按优先级匹配关键词
    for intent in INTENT_PRIORITY:
        keywords = ROUTING_RULES.get(intent, [])
        if any(kw in message_lower for kw in keywords):
            target_name = extract_target(message, context)
            return intent, target_name

    # 默认为 lead（通用对话）
    return "lead", None


def extract_target(message: str, context: Dict[str, Any]) -> Optional[str]:
    """
    从消息或上下文提取目标名称

    Args:
        message: 用户消息
        context: 当前上下文

    Returns:
        目标名称（论文标题或概念名称）
    """
    # 检查是否使用了代词
    has_pronoun = any(p in message for p in PRONOUN_PATTERNS)

    if has_pronoun:
        # 从上下文获取当前目标
        current_target = context.get("currentTarget")
        if current_target:
            return current_target.get("name")

    # 检查上传的论文
    uploaded_papers = context.get("uploadedPapers", [])
    if uploaded_papers and any(p in message for p in ["刚才上传", "上传的论文"]):
        return uploaded_papers[-1].get("title")

    # TODO: 可后续用 NER 或正则提取论文/概念名称
    # 目前返回 None，让 LLM 从上下文推断
    return None


def needs_summary(intent: str, response_length: int = 0) -> bool:
    """
    判断是否需要 Lead Agent 汇总

    Args:
        intent: 意图类型
        response_length: 响应内容长度

    Returns:
        是否需要汇总
    """
    # deep_research 总是需要汇总
    if intent == "deep_research":
        return True

    # 其他意图根据响应长度判断
    # 超过 1000 字符认为需要汇总
    if response_length > 1000:
        return True

    return False


# ============================================================
# 辅助函数
# ============================================================

def get_intent_keywords(intent: str) -> list:
    """获取某个意图的触发关键词"""
    return ROUTING_RULES.get(intent, [])


def add_intent_keyword(intent: str, keyword: str):
    """添加新的触发关键词"""
    if intent not in ROUTING_RULES:
        ROUTING_RULES[intent] = []
    if keyword not in ROUTING_RULES[intent]:
        ROUTING_RULES[intent].append(keyword)