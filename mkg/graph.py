"""
知识图谱操作模块 - 支持动态层级和双视角浏览

新设计：
- 知识点视角：按概念层级浏览（概念树）
- 论文视角：查看某概念下的所有论文
"""

from typing import List, Dict, Optional
from rich.tree import Tree
from rich.panel import Panel
from rich.text import Text


class KnowledgeGraph:
    """知识图谱操作类"""

    def __init__(self, database):
        """
        初始化

        Args:
            database: Database 实例
        """
        self.db = database

    def get_concept_tree_summary(self, max_depth: int = 3) -> str:
        """
        获取概念树的简化文本表示，用于 LLM prompt

        Args:
            max_depth: 最大深度限制

        Returns:
            概念树的缩进文本表示
        """
        roots = self.db.get_root_concepts()
        if not roots:
            return "（图谱为空）"

        lines = []

        def build_tree(concept_id: str, depth: int):
            if depth > max_depth:
                return

            concept = self.db.get_concept(concept_id)
            if not concept:
                return

            indent = "  " * depth
            lines.append(f"{indent}- {concept['text']}")

            children = self.db.get_concept_children(concept_id)
            for child in children[:10]:  # Limit children per node
                build_tree(child['id'], depth + 1)

        for root in roots[:5]:  # Limit root concepts
            build_tree(root['id'], 0)

        return "\n".join(lines)

    def build_from_paper(self, paper_doi: str, concept_tree: dict):
        """
        从论文构建图谱

        Args:
            paper_doi: 论文 DOI
            concept_tree: 概念树结构（LLM 提取的结果）
                {
                    "concept": "人工智能",
                    "category": "field",
                    "children": [...]
                }
        """
        # 使用数据库的批量方法构建概念树
        self.db.build_concept_tree_from_paper(paper_doi, concept_tree)

    def get_tree(self, root_concept: str = None, view: str = "knowledge") -> Tree:
        """
        获取树状图谱

        Args:
            root_concept: 根概念文本，默认从根概念开始
            view: 浏览模式 - "knowledge" (知识点视角) 或 "paper" (论文视角)

        Returns:
            Rich Tree
        """
        if view == "paper":
            return self._get_paper_view_tree(root_concept)
        else:
            return self._get_knowledge_view_tree(root_concept)

    def _get_knowledge_view_tree(self, root_concept: str = None) -> Tree:
        """知识点视角：显示概念层级树"""
        # 获取根节点
        if root_concept:
            root_node = self.db.get_concept_by_text(root_concept)
        else:
            roots = self.db.get_root_concepts()
            root_node = roots[0] if roots else None

        if not root_node:
            return Tree("📊 图谱为空")

        # 递归构建树
        return self._build_knowledge_tree_node(root_node)

    def _build_knowledge_tree_node(self, node: dict, depth: int = 0) -> Tree:
        """递归构建知识点树节点"""
        if depth > 10:  # 限制深度
            return Tree(f"... (更多)")

        # 节点标签
        label = f"{node['text']} ({node['paper_count']}篇)"

        # 图标
        icons = {
            "field": "🌍",
            "direction": "📚",
            "method": "⚙️",
            "technique": "🔧",
            "detail": "📁"
        }
        icon = icons.get(node.get('category', 'method'), "📁")
        label = f"{icon} {label}"

        tree = Tree(label)

        # 添加子节点
        children = self.db.get_concept_children(node['id'])
        for child in children:
            child_tree = self._build_knowledge_tree_node(child, depth + 1)
            tree.add(child_tree)

        return tree

    def _get_paper_view_tree(self, root_concept: str = None) -> Tree:
        """论文视角：显示某概念下的所有论文"""
        # 获取根节点
        if root_concept:
            root_node = self.db.get_concept_by_text(root_concept)
        else:
            roots = self.db.get_root_concepts()
            root_node = roots[0] if roots else None

        if not root_node:
            return Tree("📊 图谱为空")

        # 创建根节点
        label = f"📄 {root_node['text']} 下的论文 ({root_node['paper_count']}篇)"
        tree = Tree(label)

        # 获取直接关联的论文
        papers = self.db.get_papers_by_concept(root_node['id'])
        for paper in papers[:20]:  # 限制显示数量
            paper_label = f"📝 {paper['title'][:60]}..." if len(paper['title']) > 60 else f"📝 {paper['title']}"
            tree.add(paper_label)

        # 获取子概念及其论文
        children = self.db.get_concept_children(root_node['id'])
        if children:
            subdir = tree.add("📁 子概念")
            for child in children:
                child_papers = self.db.get_papers_by_concept(child['id'])
                child_label = f"{child['text']} ({len(child_papers)}篇)"
                child_branch = subdir.add(child_label)

                # 显示子概念下的论文（前 5 篇）
                for paper in child_papers[:5]:
                    child_branch.add(f"  📝 {paper['title'][:50]}...")

        return tree

    def list_concepts(self, parent_concept: str = None) -> List[Dict]:
        """
        列出概念

        Args:
            parent_concept: 父概念文本，为 None 时列出根概念

        Returns:
            概念列表
        """
        if parent_concept:
            parent_node = self.db.get_concept_by_text(parent_concept)
            if parent_node:
                return self.db.get_concept_children(parent_node['id'])
            return []
        else:
            return self.db.get_root_concepts()

    def list_papers(self, concept: str) -> List[Dict]:
        """
        列出某概念下的所有论文

        Args:
            concept: 概念文本

        Returns:
            论文列表
        """
        node = self.db.get_concept_by_text(concept)
        if not node:
            return []
        return self.db.get_papers_by_concept(node['id'])

    def get_concept_papers(self, concept_id: str) -> List[Dict]:
        """获取概念关联的论文"""
        return self.db.get_papers_by_concept(concept_id)

    def get_paper_concepts(self, paper_doi: str) -> List[Dict]:
        """获取论文关联的概念"""
        return self.db.get_concepts_by_paper(paper_doi)

    def get_stats(self) -> dict:
        """获取图谱统计信息"""
        return self.db.get_stats()

    def navigate(self, concept: str) -> Dict:
        """
        导航到指定概念，返回该概念的详细信息

        Args:
            concept: 概念文本

        Returns:
            概念信息，包含：
            - concept: 概念基本信息
            - parents: 父概念列表
            - children: 子概念列表
            - papers: 关联论文列表
        """
        node = self.db.get_concept_by_text(concept)
        if not node:
            return None

        return {
            'concept': node,
            'parents': self.db.get_concept_parents(node['id']),
            'children': self.db.get_concept_children(node['id']),
            'papers': self.db.get_papers_by_concept(node['id'])
        }

    def search_concepts(self, query: str) -> List[Dict]:
        """
        搜索概念

        Args:
            query: 搜索关键词

        Returns:
            匹配的概念列表
        """
        all_concepts = self.db.get_all_concepts()
        query_lower = query.lower()

        matched = []
        for concept in all_concepts:
            if query_lower in concept['text'].lower():
                matched.append(concept)

        # 按论文数排序
        matched.sort(key=lambda x: x['paper_count'], reverse=True)
        return matched[:20]
