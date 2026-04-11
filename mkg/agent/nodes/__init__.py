# mkg/agent/nodes/__init__.py
"""
LangGraph Agent Nodes - 简化版

只有 lead_node，所有功能通过 tool 调用实现
"""

from .lead import lead_node

__all__ = ["lead_node"]
