"""
OpenClaw CLI - 学术知识图谱引擎

核心工作流：PDF → LLM 概念提取 → SQLite/Neo4j 图谱 → Obsidian 导出
"""

import typer
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

from openclaw.database import Database
from openclaw.pdf_parser import PDFParser, LLMConceptExtractor, AnthropicClient, GoogleClient, OpenAICompatibleClient
from openclaw.graph import KnowledgeGraph
from openclaw.neo4j_graph import Neo4jGraph
from openclaw.obsidian_exporter import ObsidianExporter

app = typer.Typer(help="OpenClaw - 学术知识图谱引擎")
console = Console()

# 全局实例
_db = None
_graph = None
_parser = None
_extractor = None


def get_db() -> Database:
    """获取数据库实例"""
    global _db
    if _db is None:
        _db = Database("openclaw.db")
        _db.connect()
    return _db


def get_graph() -> KnowledgeGraph:
    """获取图谱实例"""
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph(get_db())
    return _graph


def get_parser() -> PDFParser:
    """获取 PDF 解析器"""
    global _parser
    if _parser is None:
        _parser = PDFParser()
    return _parser


def get_extractor() -> LLMConceptExtractor:
    """获取 LLM 概念提取器"""
    global _extractor
    if _extractor is None:
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            console.print("[red]请配置 API Key:[/red]")
            console.print("  ANTHROPIC_API_KEY, GOOGLE_API_KEY 或 DASHSCOPE_API_KEY")
            raise typer.Exit(1)

        if os.getenv("ANTHROPIC_API_KEY"):
            client = AnthropicClient(api_key)
            console.print("[green]使用 Anthropic Claude API[/green]")
        elif os.getenv("GOOGLE_API_KEY"):
            client = GoogleClient(api_key)
            console.print("[green]使用 Google Gemini API[/green]")
        else:
            client = OpenAICompatibleClient(api_key)
            console.print("[green]使用 OpenAI 兼容 API[/green]")

        _extractor = LLMConceptExtractor(client)
    return _extractor


# ========== 核心命令 ==========

@app.command()
def init():
    """初始化数据库"""
    db = get_db()
    console.print(f"[green]✓ 数据库初始化完成[/green]")
    console.print(f"  路径: {db.db_path.absolute()}")


@app.command()
def process(
    pdf_path: str = typer.Argument(..., help="PDF 文件路径"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息")
):
    """
    处理 PDF 论文：解析 + LLM 概念提取 + 构建图谱

    示例:
        openclaw process paper.pdf
        openclaw process ./papers/*.pdf
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        console.print(f"[red]文件不存在: {pdf_path}[/red]")
        raise typer.Exit(1)

    db = get_db()
    parser = get_parser()
    extractor = get_extractor()
    graph = get_graph()

    console.print(f"\n[bold]处理论文:[/bold] {pdf_file.name}\n")

    # 1. 解析 PDF
    console.print("  [dim]→ 解析 PDF...[/dim]")
    content = parser.parse(str(pdf_file))
    if not content:
        console.print("[red]PDF 解析失败[/red]")
        raise typer.Exit(1)

    if verbose:
        console.print(f"    标题: {content.title}")
        console.print(f"    作者: {', '.join(content.authors[:3])}")
        console.print(f"    文本长度: {len(content.full_text)} 字符")

    # 2. LLM 概念提取
    console.print("  [dim]→ LLM 概念提取...[/dim]")
    try:
        extracted = extractor.extract(content)
    except Exception as e:
        console.print(f"[red]LLM 提取失败: {e}[/red]")
        raise typer.Exit(1)

    concept_tree = extracted.concept_tree.to_dict() if extracted.concept_tree else None
    if not concept_tree:
        console.print("[red]概念提取失败[/red]")
        raise typer.Exit(1)

    # 3. 存储到数据库
    console.print("  [dim]→ 存储到数据库...[/dim]")
    paper_data = {
        'doi': pdf_file.stem,  # 用文件名作为 ID
        'title': extracted.title or content.title,
        'abstract': extracted.abstract or content.abstract,
        'authors': extracted.authors or content.authors,
        'pdf_path': str(pdf_file),
    }
    doi = db.add_paper(paper_data)

    # 4. 构建图谱
    console.print("  [dim]→ 构建知识图谱...[/dim]")
    graph.build_from_paper(doi, concept_tree)
    db.save_concept_extraction(doi, concept_tree, extracted.raw_response)

    # 显示结果
    console.print(f"\n[green]✓ 处理完成[/green]")
    console.print(f"  根概念: {extracted.concept_tree.concept}")
    console.print(f"  研究问题: {len(extracted.research_questions)} 个")
    console.print(f"  贡献: {len(extracted.contributions)} 个")

    if verbose and extracted.research_questions:
        console.print("\n[bold]研究问题:[/bold]")
        for q in extracted.research_questions[:3]:
            console.print(f"  • {q}")


@app.command()
def batch(
    folder: str = typer.Argument(..., help="PDF 文件夹路径"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="递归扫描子目录")
):
    """
    批量处理文件夹中的 PDF

    示例:
        openclaw batch ./papers
        openclaw batch ./papers --no-recursive
    """
    pdf_dir = Path(folder)
    if not pdf_dir.exists():
        console.print(f"[red]文件夹不存在: {folder}[/red]")
        raise typer.Exit(1)

    # 扫描 PDF
    pattern = "**/*.pdf" if recursive else "*.pdf"
    pdf_files = list(pdf_dir.glob(pattern))
    if not pdf_files:
        console.print(f"[yellow]未找到 PDF 文件[/yellow]")
        return

    console.print(f"\n[bold]发现 {len(pdf_files)} 个 PDF 文件[/bold]\n")

    success = 0
    for i, pdf_file in enumerate(pdf_files, 1):
        console.print(f"[{i}/{len(pdf_files)}] {pdf_file.name}")
        try:
            # 调用 process 命令
            process.callback(str(pdf_file), verbose=False)
            success += 1
        except Exception as e:
            console.print(f"  [red]失败: {e}[/red]")

    console.print(f"\n[green]✓ 完成: {success}/{len(pdf_files)} 篇论文处理成功[/green]")


# ========== 图谱浏览 ==========

@app.command()
def tree(
    root: str = typer.Option(None, "--root", "-r", help="根概念名称"),
    view: str = typer.Option("knowledge", "--view", "-v", help="视角: knowledge/paper")
):
    """查看知识图谱树"""
    graph = get_graph()
    console.print("\n[bold]知识图谱[/bold]\n")
    tree_view = graph.get_tree(root_concept=root, view=view)
    console.print(tree_view)


@app.command()
def ls(
    concept: str = typer.Argument(None, help="父概念名称")
):
    """列出概念（类似 ls 命令）"""
    graph = get_graph()

    if concept:
        console.print(f"\n[bold]{concept} 的子概念[/bold]\n")
    else:
        console.print("\n[bold]根概念[/bold]\n")

    concepts = graph.list_concepts(concept)
    if not concepts:
        console.print("[yellow]没有概念[/yellow]")
        return

    table = Table(show_header=True)
    table.add_column("概念")
    table.add_column("类别")
    table.add_column("论文数")

    for c in concepts:
        table.add_row(c['text'], c.get('category', '-'), str(c['paper_count']))

    console.print(table)


@app.command()
def cd(concept: str = typer.Argument(..., help="概念名称")):
    """导航到指定概念"""
    graph = get_graph()
    result = graph.navigate(concept)

    if not result:
        console.print(f"[red]概念不存在: {concept}[/red]")
        return

    console.print(f"\n[bold]📍 {result['concept']['text']}[/bold]\n")

    # 父概念
    if result['parents']:
        console.print("[bold]父概念:[/bold]")
        for p in result['parents']:
            console.print(f"  ← {p['text']}")

    # 子概念
    if result['children']:
        console.print(f"\n[bold]子概念 ({len(result['children'])} 个):[/bold]")
        for c in result['children'][:10]:
            console.print(f"  → {c['text']} ({c['paper_count']}篇)")

    # 论文
    if result['papers']:
        console.print(f"\n[bold]论文 ({len(result['papers'])} 篇):[/bold]")
        for p in result['papers'][:5]:
            console.print(f"  📄 {p['title'][:60]}...")


@app.command()
def search(query: str = typer.Argument(..., help="搜索关键词")):
    """搜索概念"""
    graph = get_graph()
    matched = graph.search_concepts(query)

    if not matched:
        console.print(f"[yellow]未找到匹配概念: {query}[/yellow]")
        return

    console.print(f"\n[bold]搜索结果: {query}[/bold]\n")

    table = Table()
    table.add_column("概念")
    table.add_column("类别")
    table.add_column("论文数")

    for c in matched:
        table.add_row(c['text'], c.get('category', '-'), str(c['paper_count']))

    console.print(table)


@app.command()
def stats():
    """显示统计信息"""
    graph = get_graph()
    stats = graph.get_stats()

    console.print("\n[bold]图谱统计[/bold]\n")

    papers = stats.get('papers', {})
    console.print(f"  论文总数: {papers.get('total', 0)}")
    for status, count in papers.items():
        if status != 'total':
            console.print(f"    - {status}: {count}")

    console.print(f"  概念总数: {stats.get('concepts', {}).get('total', 0)}")
    console.print(f"  根概念数: {stats.get('root_concepts', 0)}")
    console.print(f"  层级关系: {stats.get('relations', 0)}")


# ========== 导出 ==========

@app.command()
def export(
    vault: str = typer.Argument("obsidian_vault", help="Obsidian Vault 路径"),
    neo4j: bool = typer.Option(False, "--neo4j", help="从 Neo4j 导出")
):
    """导出到 Obsidian Vault"""
    exporter = ObsidianExporter(vault)

    if neo4j:
        console.print("\n[bold]从 Neo4j 导出...[/bold]")
        neo4j_graph = Neo4jGraph()
        if neo4j_graph.connected:
            exporter.export_from_neo4j(neo4j_graph)
        else:
            console.print("[red]Neo4j 未连接[/red]")
        neo4j_graph.close()
    else:
        console.print("\n[bold]从 SQLite 导出...[/bold]")
        db = get_db()
        graph = get_graph()
        exporter.export_from_sqlite(db, graph)


@app.command()
def neo4j_test():
    """测试 Neo4j 连接"""
    console.print("\n[bold]测试 Neo4j 连接...[/bold]\n")

    neo4j = Neo4jGraph()
    if neo4j.connected:
        console.print("[green]✓ Neo4j 连接成功[/green]")
        stats = neo4j.get_stats()
        console.print(f"  论文: {stats['papers']['total']}")
        console.print(f"  关键词: {stats['keywords']['total']}")
    else:
        console.print("[red]✗ Neo4j 连接失败[/red]")
        console.print("\n请确保:")
        console.print("  1. Neo4j 已启动")
        console.print("  2. .env 配置正确")

    neo4j.close()


@app.command()
def neo4j_migrate():
    """从 SQLite 迁移数据到 Neo4j"""
    console.print("\n[bold]从 SQLite 迁移到 Neo4j...[/bold]\n")

    neo4j = Neo4jGraph()
    if not neo4j.connected:
        console.print("[red]Neo4j 未连接[/red]")
        return

    db = get_db()

    # 迁移论文
    papers = db.get_all_papers()
    console.print(f"迁移 {len(papers)} 篇论文...")
    for paper in papers:
        neo4j.add_paper(paper)

    # 迁移概念
    concepts = db.get_all_concepts()
    console.print(f"迁移 {len(concepts)} 个概念...")
    for concept in concepts:
        neo4j.add_keyword(concept)

    # 迁移关系
    console.print("迁移概念关系...")
    # TODO: 实现关系迁移

    console.print("[green]✓ 迁移完成[/green]")
    neo4j.close()


# ========== 入口 ==========

if __name__ == "__main__":
    app()