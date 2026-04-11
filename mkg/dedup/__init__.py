"""
概念去重模块

提供概念合并与去重功能：
- CandidateGenerator: 候选对生成器
- MergeAnalyzer: LLM 分析器
- MergeExecutor: 合并执行器
- ConceptDeduplicator: 主控制器
"""

from .analyzer import MergeAnalyzer, MergeSuggestion
from .candidate import CandidateGenerator, ConceptPair
from .deduplicator import ConceptDeduplicator
from .executor import MergeExecutor, MergeResult

__all__ = [
    'CandidateGenerator', 'ConceptPair',
    'MergeAnalyzer', 'MergeSuggestion',
    'MergeExecutor', 'MergeResult',
    'ConceptDeduplicator'
]
