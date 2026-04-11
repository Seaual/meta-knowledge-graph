"""Standalone E2E pipeline runner with rich progress output.

Invocation:
    python scripts/e2e_test.py [OPTIONS]

See docs/superpowers/specs/2026-04-11-e2e-pipeline-test-design.md § 6.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import traceback
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

# Make `tests.e2e.runner` importable when the script is run from the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.e2e.fixture_metadata import FIXTURE_PDF_PATH  # noqa: E402
from tests.e2e.runner import E2EConfig, E2ERunner, E2EResult  # noqa: E402

app = typer.Typer(add_completion=False)
console = Console()

_DEFAULT_LLM_DB = _REPO_ROOT / "backend" / "mkg.db"


def _format_seconds(s: float | None) -> str:
    if s is None:
        return "skip"
    return f"{s:>6.2f}s"


def _build_summary_table(result: E2EResult) -> Table:
    table = Table(title="E2E Pipeline")
    table.add_column("Stage", style="bold")
    table.add_column("Time", justify="right")
    table.add_column("Output")

    t = result.timings
    table.add_row("Parse PDF", _format_seconds(t.parse_pdf),
                  f"{len(result.pdf_content.full_text):,} chars")
    table.add_row("LLM extraction", _format_seconds(t.extract_concepts),
                  f"root={result.extracted.concept_tree.concept}")
    table.add_row("Store paper", _format_seconds(t.store_paper),
                  f"doi={result.paper_doi}")
    table.add_row("Build graph", _format_seconds(t.build_graph),
                  f"{result.graph_stats.get('concepts', {}).get('total', 0)} concepts, "
                  f"{result.graph_stats.get('relations', 0)} relations")

    obs_output = (
        f"{result.obsidian_file_count} notes @ {result.obsidian_vault_path}"
        if result.obsidian_vault_path
        else "disabled"
    )
    table.add_row("Export Obsidian", _format_seconds(t.export_obsidian), obs_output)

    if result.neo4j_skipped_reason:
        neo_output = result.neo4j_skipped_reason
    else:
        neo_output = f"{result.neo4j_stats.get('total_concepts', 0)} concepts synced"
    table.add_row("Sync Neo4j", _format_seconds(t.sync_neo4j), neo_output)

    return table


@app.command()
def main(
    pdf: Path = typer.Option(FIXTURE_PDF_PATH, "--pdf", help="PDF to run through the pipeline"),
    work_dir: Path = typer.Option(None, "--work-dir", help="Custom work dir (default: tempfile.mkdtemp)"),
    keep_artifacts: bool = typer.Option(False, "--keep-artifacts", help="Do not delete the work dir after run"),
    no_obsidian: bool = typer.Option(False, "--no-obsidian", help="Skip Obsidian export stage"),
    no_neo4j: bool = typer.Option(False, "--no-neo4j", help="Skip Neo4j sync stage"),
    neo4j_force: bool = typer.Option(False, "--neo4j-force", help="Allow Neo4j sync even without a safe-wipe method (pollutes DB)"),
) -> None:
    console.print("[yellow]WARNING: Running with live LLM. Est. cost ~$0.10, ~30-60s[/yellow]")

    created_work_dir = False
    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix="mkg-e2e-"))
        created_work_dir = True

    config = E2EConfig(
        pdf_path=pdf,
        work_dir=work_dir,
        enable_obsidian=not no_obsidian,
        enable_neo4j=not no_neo4j,
        neo4j_force=neo4j_force,
        keep_artifacts=keep_artifacts,
        llm_config_source_db=_DEFAULT_LLM_DB if _DEFAULT_LLM_DB.exists() else None,
    )

    result: E2EResult | None = None
    try:
        with console.status("[cyan]Running pipeline..."):
            result = E2ERunner(config).run()
    except Exception:
        console.print("[red]✗ Pipeline failed[/red]")
        console.print(f"[dim]work_dir: {work_dir}[/dim]")
        console.print_exception()
        raise typer.Exit(code=1)
    finally:
        if created_work_dir and not keep_artifacts and result is not None:
            shutil.rmtree(work_dir, ignore_errors=True)

    console.print(_build_summary_table(result))
    total = (
        result.timings.parse_pdf
        + result.timings.extract_concepts
        + result.timings.store_paper
        + result.timings.build_graph
        + (result.timings.export_obsidian or 0.0)
        + (result.timings.sync_neo4j or 0.0)
    )
    console.print(f"[green]OK E2E pipeline completed in {total:.2f}s[/green]")

    if keep_artifacts:
        console.print(f"[dim]Artifacts kept at: {work_dir}[/dim]")


if __name__ == "__main__":
    app()
