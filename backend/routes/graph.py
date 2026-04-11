"""
Graph API routes
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Response

from backend.dependencies import get_db
from backend.schemas import ExportResponse, GraphData, GraphEdge, GraphNode, GraphStats
from mkg.graph import KnowledgeGraph
from mkg.obsidian_exporter import ObsidianExporter

router = APIRouter(prefix="/api/graph", tags=["graph"])

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph(get_db())
    return _graph


@router.get("/stats", response_model=GraphStats)
def get_stats():
    """Get graph statistics"""
    graph = get_graph()
    stats = graph.get_stats()
    return GraphStats(
        papers=stats.get("papers", {}),
        concepts=stats.get("concepts", {}),
        relations=stats.get("relations", 0),
        root_concepts=stats.get("root_concepts", 0),
    )


@router.get("/data", response_model=GraphData)
def get_graph_data(max_depth: int = 3, folder: str = None):
    """Get graph data for visualization, optionally filtered by folder"""
    db = get_db()

    # 如果未指定文件夹且 Neo4j 已连接，直接从 Neo4j 获取
    if not folder:
        neo4j = db.neo4j_store
        if neo4j and neo4j.connected:
            graph_data = neo4j.get_graph_data()
            nodes = [
                GraphNode(
                    id=n["id"],
                    label=n["label"],
                    label_en=n.get("label_en"),
                    category=n.get("category", "method"),
                    paper_count=n.get("paper_count", 0),
                )
                for n in graph_data["nodes"]
            ]
            edges = [
                GraphEdge(source=e["source"], target=e["target"], type="parent-child") for e in graph_data["edges"]
            ]
            return GraphData(nodes=nodes, edges=edges)

    # fallback to SQLite

    nodes = []
    edges = []

    # Get concepts filtered by folder or all
    if folder:
        concepts = db.get_concepts_by_folder(folder)
    else:
        concepts = db.get_all_concepts()
    concept_map = {c["id"]: c for c in concepts}

    # Build nodes
    for concept in concepts:
        nodes.append(
            GraphNode(
                id=concept["id"],
                label=concept["text"],
                label_en=concept.get("text_en"),
                category=concept.get("category", "method"),
                paper_count=concept.get("paper_count", 0),
            )
        )

    # Build edges from relations
    if folder:
        relations = db.get_concept_relations_by_folder(folder)
        for row in relations:
            # Only add edges where both concepts are in our filtered set
            if row["parent_id"] in concept_map and row["child_id"] in concept_map:
                edges.append(GraphEdge(source=row["parent_id"], target=row["child_id"], type="parent-child"))
    else:
        cursor = db.conn.cursor()
        cursor.execute("SELECT parent_id, child_id FROM concept_relations")
        for row in cursor.fetchall():
            edges.append(GraphEdge(source=row["parent_id"], target=row["child_id"], type="parent-child"))

    return GraphData(nodes=nodes, edges=edges)


@router.get("/tree-data")
def get_tree_data():
    """Get tree structure for D3.js hierarchical visualization"""
    db = get_db()

    # 优先使用 Neo4j
    neo4j = db.neo4j_store
    if neo4j and neo4j.connected:
        tree = neo4j.get_tree()
        if tree:
            return {"trees": [tree]}

    def build_tree(concept_id: str, depth: int = 0) -> dict:
        if depth > 10:
            return None

        concept = db.get_concept(concept_id)
        if not concept:
            return None

        node = {
            "id": concept["id"],
            "name": concept["text"],
            "category": concept.get("category"),
            "paper_count": concept.get("paper_count", 0),
            "children": [],
        }

        children = db.get_concept_children(concept_id)
        for child in children:
            child_node = build_tree(child["id"], depth + 1)
            if child_node:
                node["children"].append(child_node)

        return node

    # Get root concepts and build trees
    roots = db.get_root_concepts()
    trees = []

    for root in roots[:5]:  # Limit to 5 roots
        tree = build_tree(root["id"])
        if tree:
            trees.append(tree)

    return {"trees": trees}


@router.get("/export/obsidian", response_model=ExportResponse)
def export_obsidian(folder_id: str | None = None):
    """导出知识图谱为 Obsidian 兼容的 Markdown 格式

    Args:
        folder_id: 可选的文件夹ID，用于导出特定文件夹的内容
    """
    try:
        db = get_db()
        graph = get_graph()

        exporter = ObsidianExporter()
        content = exporter.export_overview(db, graph, folder_id=folder_id)

        if folder_id:
            papers = db.get_papers_by_folder(folder_id)
            concepts = db.get_concepts_by_folder(folder_id)
            stats = {"papers": len(papers), "concepts": len(concepts), "generated_at": datetime.now().isoformat()}
        else:
            stats = db.get_stats()
            stats = {
                "papers": stats.get("papers", {}).get("total", 0),
                "concepts": stats.get("concepts", {}).get("total", 0),
                "generated_at": datetime.now().isoformat(),
            }

        return ExportResponse(content=content, stats=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/obsidian/canvas")
def export_obsidian_canvas(folder_id: str | None = None):
    """导出知识图谱为 Obsidian Canvas 格式（带颜色和布局）"""
    try:
        db = get_db()
        graph = get_graph()

        exporter = ObsidianExporter()
        content = exporter.export_canvas(db, graph, folder_id=folder_id)

        if folder_id:
            papers = db.get_papers_by_folder(folder_id)
            concepts = db.get_concepts_by_folder(folder_id)
            stats = {"papers": len(papers), "concepts": len(concepts), "generated_at": datetime.now().isoformat()}
        else:
            stats = db.get_stats()
            stats = {
                "papers": stats.get("papers", {}).get("total", 0),
                "concepts": stats.get("concepts", {}).get("total", 0),
                "generated_at": datetime.now().isoformat(),
            }

        return {"content": content, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/obsidian/canvas/download")
def download_obsidian_canvas(folder_id: str | None = None):
    """下载 Obsidian Canvas 文件（.canvas 格式）"""
    try:
        db = get_db()
        graph = get_graph()

        exporter = ObsidianExporter()
        content = exporter.export_canvas(db, graph, folder_id=folder_id)

        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=knowledge-graph-{datetime.now().strftime('%Y%m%d')}.canvas"
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/obsidian/download")
def download_obsidian(folder_id: str | None = None):
    """下载 Obsidian Markdown 文件"""
    try:
        db = get_db()
        graph = get_graph()

        exporter = ObsidianExporter()
        content = exporter.export_overview(db, graph, folder_id=folder_id)

        return Response(
            content=content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename=knowledge-graph-{datetime.now().strftime('%Y%m%d')}.md"
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/obsidian/html")
def export_obsidian_html(folder_id: str | None = None):
    """导出知识图谱为交互式 HTML 页面（D3.js 力导向图）"""
    try:
        db = get_db()
        graph = get_graph()

        exporter = ObsidianExporter()
        content = exporter.export_html(db, graph, folder_id=folder_id)

        if folder_id:
            papers = db.get_papers_by_folder(folder_id)
            concepts = db.get_concepts_by_folder(folder_id)
            stats = {"papers": len(papers), "concepts": len(concepts), "generated_at": datetime.now().isoformat()}
        else:
            stats = db.get_stats()
            stats = {
                "papers": stats.get("papers", {}).get("total", 0),
                "concepts": stats.get("concepts", {}).get("total", 0),
                "generated_at": datetime.now().isoformat(),
            }

        return {"content": content, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/obsidian/html/download")
def download_obsidian_html(folder_id: str | None = None):
    """下载交互式 HTML 文件（带物理渲染）"""
    try:
        db = get_db()
        graph = get_graph()

        exporter = ObsidianExporter()
        content = exporter.export_html(db, graph, folder_id=folder_id)

        return Response(
            content=content,
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename=knowledge-graph-{datetime.now().strftime('%Y%m%d')}.html"
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
