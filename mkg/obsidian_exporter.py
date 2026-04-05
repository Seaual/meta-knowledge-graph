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

    def export_from_sqlite(self, db, graph, output_name: str = "mkg_knowledge"):
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

    def export_overview(self, db, graph, folder_id=None) -> str:
        """导出图谱总览（单个Markdown文件）

        Args:
            db: 数据库实例
            graph: 知识图谱实例
            folder_id: 可选的文件夹ID，用于导出特定文件夹的内容
        """
        if folder_id:
            concepts = db.get_concepts_by_folder(folder_id)
            papers = db.get_papers_by_folder(folder_id)
        else:
            concepts = db.get_all_concepts()
            papers = db.get_all_papers()

        lines = []
        lines.append("# 知识图谱总览\n")
        lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 论文: {len(papers)} 篇 | 概念: {len(concepts)} 个\n")

        # Build parent map
        parent_map = {}
        for concept in concepts:
            parents = db.get_concept_parents(concept['id'])
            if parents:
                parent_map[concept['id']] = parents[0]['id']

        # Find root concepts (no parent)
        root_ids = [c['id'] for c in concepts if c['id'] not in parent_map]

        # Build children map
        children_map = {}
        for concept in concepts:
            children = db.get_concept_children(concept['id'])
            children_map[concept['id']] = [c['id'] for c in children]

        # Concept hierarchy section
        lines.append("## 概念层级\n")

        def format_tree(concept_id: str, indent: int = 0) -> List[str]:
            concept = next((c for c in concepts if c['id'] == concept_id), None)
            if not concept:
                return []
            result = []
            prefix = "  " * indent + "- " if indent > 0 else "### "
            result.append(f"{prefix}[[{concept['text']}]]\n")
            for child_id in children_map.get(concept_id, []):
                result.extend(format_tree(child_id, indent + 1 if indent > 0 else 1))
            return result

        for root_id in root_ids[:10]:
            lines.extend(format_tree(root_id))

        lines.append("\n## 概念详情\n")

        # Concept details
        for concept in concepts[:50]:
            lines.append(f"### {concept['text']}\n")
            lines.append(f"- **类别**: {concept.get('category', 'method')}\n")
            lines.append(f"- **关联论文**: {concept.get('paper_count', 0)} 篇\n")

            # Children
            children = children_map.get(concept['id'], [])
            if children:
                child_texts = []
                for child_id in children:
                    child = next((c for c in concepts if c['id'] == child_id), None)
                    if child:
                        child_texts.append(f"[[{child['text']}]]")
                lines.append(f"- **子概念**: {', '.join(child_texts)}\n")

            # Parents
            parent_id = parent_map.get(concept['id'])
            if parent_id:
                parent = next((c for c in concepts if c['id'] == parent_id), None)
                if parent:
                    lines.append(f"- **父概念**: [[{parent['text']}]]\n")

            lines.append("\n")

        return "".join(lines)

    def export_canvas(self, db, graph, folder_id=None) -> str:
        """
        导出为 Obsidian Canvas 格式（.canvas 文件）

        Canvas 支持：
        - 节点颜色（按概念类别）
        - 节点位置（树状布局）
        - 节点连线（父子关系）

        Args:
            db: 数据库实例
            graph: 知识图谱实例
            folder_id: 可选的文件夹ID
        """
        if folder_id:
            concepts = db.get_concepts_by_folder(folder_id)
        else:
            concepts = db.get_all_concepts()

        # 类别到颜色的映射
        category_colors = {
            'field': '1',      # 红色 - 大领域
            'direction': '5',  # 青色 - 研究方向
            'subdirection': '5',
            'task': '6',       # 紫色 - 任务
            'method': '2',     # 橙色 - 方法
            'technique': '3',  # 黄色 - 技术
            'detail': '4',     # 绿色 - 细节
        }

        # 构建父子关系映射
        parent_map = {}
        children_map = {}
        concept_by_id = {}

        for concept in concepts:
            concept_by_id[concept['id']] = concept
            children_map[concept['id']] = []

        for concept in concepts:
            parents = db.get_concept_parents(concept['id'])
            if parents:
                parent_map[concept['id']] = parents[0]['id']
                children_map[parents[0]['id']].append(concept['id'])

        # 找根节点
        root_ids = [c['id'] for c in concepts if c['id'] not in parent_map]

        # 布局参数
        node_width = 200
        node_height = 60
        horizontal_gap = 50
        vertical_gap = 100

        nodes = []
        edges = []

        # 计算每个节点的位置（树状布局）
        node_positions = {}

        def calculate_subtree_width(concept_id: str) -> int:
            """计算子树宽度（用于布局）"""
            children = children_map.get(concept_id, [])
            if not children:
                return 1
            return sum(calculate_subtree_width(c) for c in children)

        def layout_tree(concept_id: str, x: float, y: float) -> None:
            """递归布局树节点"""
            concept = concept_by_id.get(concept_id)
            if not concept:
                return

            # 当前节点位置
            node_positions[concept_id] = (x, y)

            # 子节点
            children = children_map.get(concept_id, [])
            if not children:
                return

            # 计算子树总宽度
            total_width = sum(calculate_subtree_width(c) for c in children)
            current_x = x - (total_width - 1) * (node_width + horizontal_gap) / 2

            for child_id in children:
                child_width = calculate_subtree_width(child_id)
                child_x = current_x + (child_width - 1) * (node_width + horizontal_gap) / 2
                layout_tree(child_id, child_x, y + vertical_gap + node_height)
                current_x += child_width * (node_width + horizontal_gap)

        # 从根节点开始布局
        total_roots = len(root_ids[:10])
        root_start_x = -(total_roots - 1) * (node_width + horizontal_gap * 3) / 2

        for i, root_id in enumerate(root_ids[:10]):
            root_x = root_start_x + i * (node_width + horizontal_gap * 3)
            layout_tree(root_id, root_x, 0)

        # 生成节点和边
        node_id_counter = 0
        concept_to_node_id = {}

        for concept_id, (x, y) in node_positions.items():
            concept = concept_by_id.get(concept_id)
            if not concept:
                continue

            node_id = f"node_{node_id_counter}"
            concept_to_node_id[concept_id] = node_id
            node_id_counter += 1

            category = concept.get('category', 'method')
            color = category_colors.get(category, '4')

            nodes.append({
                "id": node_id,
                "type": "text",
                "text": concept['text'],
                "x": x,
                "y": y,
                "width": node_width,
                "height": node_height,
                "color": color
            })

        # 生成边
        edge_id_counter = 0
        for concept_id, parent_id in parent_map.items():
            if concept_id in concept_to_node_id and parent_id in concept_to_node_id:
                edges.append({
                    "id": f"edge_{edge_id_counter}",
                    "fromNode": concept_to_node_id[parent_id],
                    "toNode": concept_to_node_id[concept_id]
                })
                edge_id_counter += 1

        canvas_data = {
            "nodes": nodes,
            "edges": edges
        }

        return json.dumps(canvas_data, ensure_ascii=False, indent=2)

    def export_html(self, db, graph, folder_id=None) -> str:
        """
        导出为交互式 HTML 页面

        支持功能：
        - D3.js 力导向图物理渲染
        - 节点拖拽
        - 缩放平移
        - 节点按类别着色
        - 悬停显示详情

        Args:
            db: 数据库实例
            graph: 知识图谱实例
            folder_id: 可选的文件夹ID
        """
        if folder_id:
            concepts = db.get_concepts_by_folder(folder_id)
            papers = db.get_papers_by_folder(folder_id)
        else:
            concepts = db.get_all_concepts()
            papers = db.get_all_papers()

        # 类别到颜色的映射
        category_colors = {
            'field': '#FF6B6B',      # 红色 - 大领域
            'direction': '#4ECDC4',  # 青色 - 研究方向
            'subdirection': '#45B7D1',
            'task': '#A78BFA',       # 紫色 - 任务
            'method': '#FFA726',     # 橙色 - 方法
            'technique': '#FFD93D',  # 黄色 - 技术
            'detail': '#96CEB4',     # 绿色 - 细节
        }

        # 构建节点数据
        nodes = []
        concept_by_id = {}
        for c in concepts:
            concept_by_id[c['id']] = c
            nodes.append({
                "id": c['id'],
                "text": c['text'],
                "category": c.get('category', 'method'),
                "paper_count": c.get('paper_count', 0)
            })

        # 构建边数据
        links = []
        for c in concepts:
            parents = db.get_concept_parents(c['id'])
            for p in parents:
                links.append({
                    "source": p['id'],
                    "target": c['id']
                })

        # 生成HTML
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>知识图谱 - 交互式可视化</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            overflow: hidden;
        }}
        #container {{
            width: 100vw;
            height: 100vh;
        }}
        .node {{
            cursor: pointer;
        }}
        .node circle {{
            stroke-width: 2px;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
        }}
        .node text {{
            font-size: 11px;
            fill: #fff;
            text-anchor: middle;
            pointer-events: none;
            text-shadow: 0 1px 2px rgba(0,0,0,0.8);
        }}
        .link {{
            stroke: rgba(255,255,255,0.2);
            stroke-width: 1.5px;
        }}
        .tooltip {{
            position: absolute;
            background: rgba(30, 41, 59, 0.95);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 12px 16px;
            color: #fff;
            font-size: 13px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            max-width: 300px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
            z-index: 100;
        }}
        .tooltip.visible {{
            opacity: 1;
        }}
        .tooltip h3 {{
            margin-bottom: 8px;
            font-size: 15px;
        }}
        .tooltip .category {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            margin-bottom: 6px;
        }}
        .tooltip .paper-count {{
            color: rgba(255,255,255,0.7);
            font-size: 12px;
        }}
        #info {{
            position: fixed;
            top: 20px;
            left: 20px;
            background: rgba(30, 41, 59, 0.9);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 16px 20px;
            color: #fff;
            z-index: 10;
        }}
        #info h1 {{
            font-size: 18px;
            margin-bottom: 8px;
        }}
        #info p {{
            font-size: 13px;
            color: rgba(255,255,255,0.7);
        }}
        #legend {{
            position: fixed;
            bottom: 20px;
            left: 20px;
            background: rgba(30, 41, 59, 0.9);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 16px;
            color: #fff;
            z-index: 10;
        }}
        #legend h3 {{
            font-size: 14px;
            margin-bottom: 10px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
            font-size: 12px;
        }}
        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}
        #controls {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            display: flex;
            gap: 10px;
            z-index: 10;
        }}
        #controls button {{
            background: rgba(30, 41, 59, 0.9);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            padding: 10px 16px;
            color: #fff;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }}
        #controls button:hover {{
            background: rgba(59, 130, 246, 0.5);
        }}
    </style>
</head>
<body>
    <div id="container"></div>
    <div id="info">
        <h1>知识图谱</h1>
        <p>概念: {len(concepts)} 个 | 论文: {len(papers)} 篇</p>
        <p style="margin-top: 6px; font-size: 11px;">拖拽节点 | 滚轮缩放</p>
    </div>
    <div id="legend">
        <h3>概念层级</h3>
        <div class="legend-item"><div class="legend-color" style="background: #FF6B6B"></div>领域 (field)</div>
        <div class="legend-item"><div class="legend-color" style="background: #4ECDC4"></div>方向 (direction)</div>
        <div class="legend-item"><div class="legend-color" style="background: #A78BFA"></div>任务 (task)</div>
        <div class="legend-item"><div class="legend-color" style="background: #FFA726"></div>方法 (method)</div>
        <div class="legend-item"><div class="legend-color" style="background: #FFD93D"></div>技术 (technique)</div>
    </div>
    <div id="controls">
        <button onclick="resetZoom()">重置视图</button>
        <button onclick="togglePhysics()">暂停/继续物理</button>
    </div>
    <div class="tooltip" id="tooltip"></div>

    <script>
        const nodes = {json.dumps(nodes, ensure_ascii=False)};
        const links = {json.dumps(links, ensure_ascii=False)};
        const categoryColors = {json.dumps(category_colors)};

        const width = window.innerWidth;
        const height = window.innerHeight;

        const svg = d3.select("#container")
            .append("svg")
            .attr("width", width)
            .attr("height", height);

        const container = svg.append("g");

        // Zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => {{
                container.attr("transform", event.transform);
            }});

        svg.call(zoom);

        // Arrow marker
        svg.append("defs").append("marker")
            .attr("id", "arrowhead")
            .attr("viewBox", "-0 -5 10 10")
            .attr("refX", 20)
            .attr("refY", 0)
            .attr("orient", "auto")
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .append("path")
            .attr("d", "M 0,-5 L 10,0 L 0,5")
            .attr("fill", "rgba(255,255,255,0.3)");

        // Links
        const link = container.append("g")
            .selectAll("line")
            .data(links)
            .enter().append("line")
            .attr("class", "link")
            .attr("marker-end", "url(#arrowhead)");

        // Nodes
        const node = container.append("g")
            .selectAll("g")
            .data(nodes)
            .enter().append("g")
            .attr("class", "node")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));

        // Node circles
        node.append("circle")
            .attr("r", d => 8 + Math.sqrt(d.paper_count || 0) * 2)
            .attr("fill", d => categoryColors[d.category] || '#94A3B8')
            .attr("stroke", d => categoryColors[d.category] || '#94A3B8')
            .attr("stroke-opacity", 0.5);

        // Node labels
        node.append("text")
            .attr("dy", d => 14 + Math.sqrt(d.paper_count || 0) * 2)
            .text(d => d.text.length > 10 ? d.text.substring(0, 10) + '...' : d.text);

        // Tooltip
        const tooltip = d3.select("#tooltip");

        node.on("mouseover", function(event, d) {{
            d3.select(this).select("circle").attr("stroke-width", 4);
            tooltip.html(`
                <h3>${{d.text}}</h3>
                <div class="category" style="background: ${{categoryColors[d.category]}}20; color: ${{categoryColors[d.category]}}">
                    ${{d.category}}
                </div>
                <div class="paper-count">关联论文: ${{d.paper_count || 0}} 篇</div>
            `)
            .style("left", (event.pageX + 15) + "px")
            .style("top", (event.pageY - 10) + "px")
            .classed("visible", true);
        }})
        .on("mousemove", function(event, d) {{
            tooltip
                .style("left", (event.pageX + 15) + "px")
                .style("top", (event.pageY - 10) + "px");
        }})
        .on("mouseout", function(event, d) {{
            d3.select(this).select("circle").attr("stroke-width", 2);
            tooltip.classed("visible", false);
        }});

        // Force simulation
        const simulation = d3.forceSimulation(nodes)
            .force("link", d3.forceLink(links).id(d => d.id).distance(80).strength(0.5))
            .force("charge", d3.forceManyBody().strength(-200))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(d => 20 + Math.sqrt(d.paper_count || 0) * 2))
            .on("tick", ticked);

        function ticked() {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node.attr("transform", d => `translate(${{d.x}}, ${{d.y}})`);
        }}

        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}

        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}

        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}

        function resetZoom() {{
            svg.transition().duration(500).call(
                zoom.transform,
                d3.zoomIdentity.translate(width / 2, height / 2).scale(0.8).translate(-width / 2, -height / 2)
            );
        }}

        let physicsPaused = false;
        function togglePhysics() {{
            physicsPaused = !physicsPaused;
            if (physicsPaused) {{
                simulation.stop();
            }} else {{
                simulation.alpha(1).restart();
            }}
        }}

        // Initial zoom
        svg.call(zoom.transform, d3.zoomIdentity.translate(width / 2, height / 2).scale(0.8).translate(-width / 2, -height / 2));
    </script>
</body>
</html>'''

        return html

    def export_from_neo4j(self, neo4j_graph, output_name: str = "mkg_knowledge"):
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