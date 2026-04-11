"""E2E pipeline runner.

Drives the full mkg pipeline: PDF → LLM → SQLite → KnowledgeGraph →
Obsidian → Neo4j. Pure logic, no asserts, no rich output. Callers decide how
to display results.

See docs/superpowers/specs/2026-04-11-e2e-pipeline-test-design.md for the
full design.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class E2EConfig:
    pdf_path: Path
    work_dir: Path
    enable_neo4j: bool = True
    enable_obsidian: bool = True
    keep_artifacts: bool = False
    neo4j_force: bool = False  # Allow Neo4j sync without a safe-wipe method
    llm_config_source_db: Path | None = None  # Copy LLM config from here if set


@dataclass(frozen=True)
class StageTimings:
    parse_pdf: float
    extract_concepts: float
    store_paper: float
    build_graph: float
    export_obsidian: float | None
    sync_neo4j: float | None


@dataclass(frozen=True)
class E2EResult:
    config: E2EConfig
    pdf_content: Any               # mkg.pdf_models.PaperContent | None
    extracted: Any                 # mkg.pdf_models.LLMExtractedContent | None
    paper_doi: str
    graph_stats: dict
    graph_tree_text: str
    obsidian_vault_path: Path | None
    obsidian_file_count: int
    neo4j_stats: dict | None
    neo4j_skipped_reason: str | None
    timings: StageTimings
    db_path: Path


# ---- Safety helpers -------------------------------------------------------


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_FORBIDDEN_PREFIXES = (
    _PROJECT_ROOT / "backend",
    _PROJECT_ROOT / "mkg",
    _PROJECT_ROOT / "papers",
    _PROJECT_ROOT / "obsidian_vault",
)


def _validate_work_dir(work_dir: Path) -> None:
    """Raise ValueError if work_dir is unsafe to use as an E2E scratch dir.

    Safe: a nonexistent path, OR an existing empty directory, that is NOT the
    repo root and NOT inside backend/mkg/papers/obsidian_vault.
    """
    resolved = work_dir.resolve()

    if resolved == _PROJECT_ROOT:
        raise ValueError(f"work_dir must not be the project root: {resolved}")

    for forbidden in _FORBIDDEN_PREFIXES:
        try:
            resolved.relative_to(forbidden)
        except ValueError:
            continue
        raise ValueError(
            f"work_dir is inside a protected path ({forbidden.name}): {resolved}"
        )

    if resolved.exists():
        if not resolved.is_dir():
            raise ValueError(f"work_dir exists and is not a directory: {resolved}")
        if any(resolved.iterdir()):
            raise ValueError(f"work_dir exists and is not empty: {resolved}")


# ---- Timing helper -----------------------------------------------------


class _Timer:
    """Tiny mutable holder for elapsed time from `_timed()`."""

    def __init__(self) -> None:
        self.elapsed: float = 0.0


@contextmanager
def _timed():
    """Context manager that measures wall-clock seconds.

    Usage:
        with _timed() as t:
            do_work()
        print(t.elapsed)

    Records elapsed time even if the body raises.
    """
    timer = _Timer()
    start = time.perf_counter()
    try:
        yield timer
    finally:
        timer.elapsed = time.perf_counter() - start


# ---- Tree rendering ----------------------------------------------------


def _render_tree_text(tree) -> str:
    """Render a rich.tree.Tree to a plain string.

    `KnowledgeGraph.get_tree()` returns a rich Tree object, not a string.
    We render it through a StringIO-backed Console so we can store the result
    in `E2EResult.graph_tree_text` for later assertions and script display.
    """
    from rich.console import Console

    buf = StringIO()
    # width=120 so long concept labels don't wrap mid-word
    Console(file=buf, width=120, force_terminal=False).print(tree)
    return buf.getvalue()
