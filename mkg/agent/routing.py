# mkg/agent/routing.py
"""
意图路由 - 简化版

所有请求都路由到 lead agent，由 lead agent 通过 tool 调用决定具体功能
"""

from typing import Any


def route_intent(message: str, context: dict[str, Any] | None = None) -> tuple[str, str | None]:
    """
    简化的路由：所有请求都路由到 lead agent

    Args:
        message: 用户消息
        context: 当前上下文

    Returns:
        ("lead", None) - 始终路由到 lead
    """
    return "lead", None
