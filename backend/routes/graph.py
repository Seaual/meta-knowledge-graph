"""
Graph API routes
"""

from fastapi import APIRouter, Response, HTTPException
from typing import List
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from openclaw.database import Database
from openclaw.graph import KnowledgeGraph
from openclaw.obsidian_exporter import ObsidianExporter
from backend.schemas import GraphStats, GraphData, GraphNode, GraphEdge, ExportResponse

router = APIRouter(prefix="/api/graph", tags=["graph"])

_db = None
_graph = None


def get_db():
    global _db
    if _db is None:
        _db = Database("openclaw.db")
        _db.connect()
    return _db


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
        papers=stats.get('papers', {}),
        concepts=stats.get('concepts', {}),
        relations=stats.get('relations', 0),
        root_concepts=stats.get('root_concepts', 0)
    )


@router.get("/data", response_model=GraphData)
def get_graph_data(max_depth: int = 3, folder: str = None):
    """Get graph data for visualization, optionally filtered by folder"""
    db = get_db()
    graph = get_graph()

    nodes = []
    edges = []

    # Get concepts filtered by folder or all
    if folder:
        concepts = db.get_concepts_by_folder(folder)
    else:
        concepts = db.get_all_concepts()
    concept_map = {c['id']: c for c in concepts}

    # Build nodes
    for concept in concepts:
        nodes.append(GraphNode(
            id=concept['id'],
            label=concept['text'],
            category=concept.get('category', 'method'),
            paper_count=concept.get('paper_count', 0)
        ))

    # Build edges from relations
    if folder:
        relations = db.get_concept_relations_by_folder(folder)
        for row in relations:
            # Only add edges where both concepts are in our filtered set
            if row['parent_id'] in concept_map and row['child_id'] in concept_map:
                edges.append(GraphEdge(
                    source=row['parent_id'],
                    target=row['child_id'],
                    type="parent-child"
                ))
    else:
        cursor = db.conn.cursor()
        cursor.execute("SELECT parent_id, child_id FROM concept_relations")
        for row in cursor.fetchall():
            edges.append(GraphEdge(
                source=row['parent_id'],
                target=row['child_id'],
                type="parent-child"
            ))

    return GraphData(nodes=nodes, edges=edges)


@router.get("/tree-data")
def get_tree_data():
    """Get tree structure for D3.js hierarchical visualization"""
    db = get_db()

    def build_tree(concept_id: str, depth: int = 0) -> dict:
        if depth > 10:
            return None

        concept = db.get_concept(concept_id)
        if not concept:
            return None

        node = {
            "id": concept['id'],
            "name": concept['text'],
            "category": concept.get('category'),
            "paper_count": concept.get('paper_count', 0),
            "children": []
        }

        children = db.get_concept_children(concept_id)
        for child in children:
            child_node = build_tree(child['id'], depth + 1)
            if child_node:
                node['children'].append(child_node)

        return node

    # Get root concepts and build trees
    roots = db.get_root_concepts()
    trees = []

    for root in roots[:5]:  # Limit to 5 roots
        tree = build_tree(root['id'])
        if tree:
            trees.append(tree)

    return {"trees": trees}


@router.get("/export/obsidian", response_model=ExportResponse)
def export_obsidian():
    """导出知识图谱为 Obsidian 兼容的 Markdown 格式"""
    try:
        db = get_db()
        graph = get_graph()

        exporter = ObsidianExporter()
        content = exporter.export_overview(db, graph)

        stats = db.get_stats()

        return ExportResponse(
            content=content,
            stats={
                "papers": stats.get('papers', {}).get('total', 0),
                "concepts": stats.get('concepts', {}).get('total', 0),
                "generated_at": datetime.now().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/obsidian/canvas")
def export_obsidian_canvas():
    """导出知识图谱为 Obsidian Canvas 格式（带颜色和布局）"""
    try:
        db = get_db()
        graph = get_graph()

        exporter = ObsidianExporter()
        content = exporter.export_canvas(db, graph)

        stats = db.get_stats()

        return {
            "content": content,
            "stats": {
                "papers": stats.get('papers', {}).get('total', 0),
                "concepts": stats.get('concepts', {}).get('total', 0),
                "generated_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/obsidian/canvas/download")
def download_obsidian_canvas():
    """下载 Obsidian Canvas 文件（.canvas 格式）"""
    try:
        db = get_db()
        graph = get_graph()

        exporter = ObsidianExporter()
        content = exporter.export_canvas(db, graph)

        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=knowledge-graph-{datetime.now().strftime('%Y%m%d')}.canvas"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/obsidian/download")
def download_obsidian():
    """下载 Obsidian Markdown 文件"""
    try:
        db = get_db()
        graph = get_graph()

        exporter = ObsidianExporter()
        content = exporter.export_overview(db, graph)

        return Response(
            content=content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename=knowledge-graph-{datetime.now().strftime('%Y%m%d')}.md"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/obsidian/html")
def export_obsidian_html():
    """导出知识图谱为交互式 HTML 页面（D3.js 力导向图）"""
    try:
        db = get_db()
        graph = get_graph()

        exporter = ObsidianExporter()
        content = exporter.export_html(db, graph)

        stats = db.get_stats()

        return {
            "content": content,
            "stats": {
                "papers": stats.get('papers', {}).get('total', 0),
                "concepts": stats.get('concepts', {}).get('total', 0),
                "generated_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/obsidian/html/download")
def download_obsidian_html():
    """下载交互式 HTML 文件（带物理渲染）"""
    try:
        db = get_db()
        graph = get_graph()

        exporter = ObsidianExporter()
        content = exporter.export_html(db, graph)

        return Response(
            content=content,
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename=knowledge-graph-{datetime.now().strftime('%Y%m%d')}.html"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
