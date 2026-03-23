"""
Obsidian 知识图谱导出器

将 OpenClaw 的知识图谱导出为 Obsidian 可用的 Markdown 格式
支持 SQLite 和 Neo4j 两种后端
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict


class ObsidianExporter:
    """
    Obsidian 导出器

    导出结构:
    vault/
    ├── Papers/           # 论文笔记
    ├── Concepts/         # 概念笔记
    └── Maps/             # 索引文件
    """

    def __init__(self, vault_path: str = "obsidian_vault"):
        self.vault_path = Path(vault_path)
        self.papers_dir = self.vault_path / "Papers"
        self.concepts_dir = self.vault_path / "Concepts"
        self.maps_dir = self.vault_path / "Maps"

        # 创建目录
        self.papers_dir.mkdir(parents=True, exist_ok=True)
        self.concepts_dir.mkdir(parents=True, exist_ok=True)
        self.maps_dir.mkdir(parents=True, exist_ok=True)

        self.stats = {'papers': 0, 'concepts': 0}

    def export_from_sqlite(self, db, graph, output_name: str = "openclaw_knowledge"):
        """从 SQLite 数据库导出"""
        print(f"\n导出到: {self.vault_path}\n")

        # 导出所有概念
        all_concepts = db.get_all_concepts()
        print(f"导出 {len(all_concepts)} 个概念...")
        for concept in all_concepts:
            self._export_concept(concept, db)
            self.stats['concepts'] += 1

        # 导出所有论文
        all_papers = db.get_all_papers()
        print(f"导出 {len(all_papers)} 篇论文...")
        for paper in all_papers:
            self._export_paper(paper, db)
            self.stats['papers'] += 1

        # 创建索引
        self._create_index(all_concepts, all_papers, output_name)

        print(f"\n✓ 导出完成!")
        print(f"  论文: {self.stats['papers']} 篇")
        print(f"  概念: {self.stats['concepts']} 个")
        print(f"  路径: {self.vault_path.absolute()}")

    def export_from_neo4j(self, neo4j_graph, output_name: str = "openclaw_knowledge"):
        """从 Neo4j 导出"""
        print(f"\n导出到: {self.vault_path}\n")

        if not neo4j_graph.connected:
            print("Neo4j 未连接")
            return

        # TODO: 实现 Neo4j 导出
        print("Neo4j 导出待实现")

    def _export_concept(self, concept: Dict, db):
        """导出概念"""
        concept_id = concept.get('id', '')
        text = concept.get('text', 'unknown')
        category = concept.get('category', 'method')
        paper_count = concept.get('paper_count', 0)

        filename = f"{self._safe_filename(text)}.md"
        filepath = self.concepts_dir / filename

        # 获取父子关系
        children = db.get_concept_children(concept_id)
        parents = db.get_concept_parents(concept_id)
        papers = db.get_papers_by_concept(concept_id)

        lines = []
        # Frontmatter
        lines.append("---")
        lines.append(f"category: {category}")
        lines.append(f"paper_count: {paper_count}")
        lines.append("tags: [concept]")
        lines.append("---")
        lines.append("")

        # 标题
        lines.append(f"# {text}")
        lines.append("")

        # 层级位置
        if parents:
            parent_links = [f"[[{p['text']}]]" for p in parents]
            lines.append(f"**路径**: {' > '.join(parent_links)} > {text}")
            lines.append("")

        # 子概念
        lines.append("## 子概念")
        lines.append("")
        if children:
            for child in children:
                lines.append(f"- [[{child['text']}]] ({child['paper_count']}篇)")
        else:
            lines.append("*无子概念*")
        lines.append("")

        # 关联论文
        lines.append("## 相关论文")
        lines.append("")
        if papers:
            for paper in papers[:10]:
                title = paper.get('title', 'Untitled')[:60]
                lines.append(f"- [[{title}]]")
            if len(papers) > 10:
                lines.append(f"\n*还有 {len(papers) - 10} 篇...*")
        else:
            lines.append("*无关联论文*")
        lines.append("")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

    def _export_paper(self, paper: Dict, db):
        """导出论文"""
        doi = paper.get('doi', '')
        title = paper.get('title', 'Untitled')
        abstract = paper.get('abstract', '')
        authors = paper.get('authors', [])

        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except:
                authors = []

        filename = f"{self._safe_filename(title[:50])}.md"
        filepath = self.papers_dir / filename

        # 获取关联概念
        concepts = db.get_concepts_by_paper(doi)

        lines = []
        # Frontmatter
        lines.append("---")
        lines.append(f"doi: {doi}")
        lines.append(f"authors: {json.dumps(authors, ensure_ascii=False)}")
        lines.append("tags: [paper]")
        lines.append("---")
        lines.append("")

        lines.append(f"# {title}")
        lines.append("")

        if authors:
            lines.append(f"**作者**: {', '.join(authors[:5])}")
            lines.append("")

        lines.append("## 摘要")
        lines.append("")
        lines.append(abstract[:1000] if abstract else "*无摘要*")
        lines.append("")

        lines.append("## 相关概念")
        lines.append("")
        if concepts:
            for c in concepts:
                lines.append(f"- [[{c['text']}]]")
        else:
            lines.append("*无概念*")
        lines.append("")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

    def _create_index(self, concepts: List, papers: List, output_name: str):
        """创建索引文件"""
        filepath = self.maps_dir / "index.md"

        lines = []
        lines.append("# 知识图谱索引")
        lines.append("")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"论文: {len(papers)} 篇 | 概念: {len(concepts)} 个")
        lines.append("")

        # 根概念
        lines.append("## 根概念")
        lines.append("")
        root_concepts = [c for c in concepts if not c.get('depth_cache', -1) == 0]
        for c in root_concepts[:20]:
            lines.append(f"- [[{c['text']}]] ({c['paper_count']}篇)")
        lines.append("")

        # 最新论文
        lines.append("## 最新论文")
        lines.append("")
        for paper in papers[:10]:
            title = paper.get('title', 'Untitled')[:50]
            lines.append(f"- [[{title}]]")
        lines.append("")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

    def _safe_filename(self, text: str) -> str:
        """生成安全的文件名"""
        unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in unsafe_chars:
            text = text.replace(char, '_')
        return text.strip()[:100]