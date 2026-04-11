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


# ---- LLM config copying ------------------------------------------------


def _copy_llm_config(src: Path, dst) -> None:
    """Copy LLM config from `src` (a SQLite file) into the already-open `dst` Database.

    The real `mkg.database.Database` API (verified at plan time):
      - get_llm_config() -> dict | None   # returns {"mode": str, "providers": list[dict], ...}
      - save_llm_config(mode: str, providers: list[dict]) -> dict
      - provider activeness lives in each provider dict's `is_active` field; no
        separate "set active" method.

    `save_llm_config` replaces the destination config entirely, which is fine
    since `dst` is a fresh isolated test db.
    """
    from mkg.database import Database

    src_db = Database(str(src))
    src_db.connect()
    try:
        config = src_db.get_llm_config()
        if not config or not config.get("providers"):
            raise RuntimeError(
                f"Source database has no LLM config: {src}. "
                f"Configure a provider via the backend / CLI before running E2E tests."
            )
        dst.save_llm_config(
            mode=config.get("mode", "single"),
            providers=config["providers"],
        )
    finally:
        src_db.close()


# ---- Runner ------------------------------------------------------------


class E2ERunner:
    """Drives one full mkg pipeline run and returns an immutable E2EResult.

    Each call to `run()` is ONE live LLM call. Callers (pytest fixture,
    script) should invoke `run()` exactly once per session and share the
    result with downstream consumers.
    """

    def __init__(self, config: E2EConfig) -> None:
        if not config.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {config.pdf_path}")
        if config.pdf_path.stat().st_size == 0:
            raise ValueError(f"PDF is empty: {config.pdf_path}")
        _validate_work_dir(config.work_dir)
        self.config = config

    def run(self) -> E2EResult:
        from mkg.concept_extractor import LLMConceptExtractor
        from mkg.database import Database
        from mkg.graph import KnowledgeGraph
        from mkg.llm import init_llm_from_db
        from mkg.obsidian_exporter import ObsidianExporter

        cfg = self.config
        cfg.work_dir.mkdir(parents=True, exist_ok=True)
        db_path = cfg.work_dir / "mkg.db"

        db = Database(str(db_path))
        db.connect()
        neo4j_store = None

        try:
            # Seed LLM config from source db if requested
            if cfg.llm_config_source_db is not None:
                _copy_llm_config(cfg.llm_config_source_db, db)

            # ---- Stage 1: Parse PDF --------------------------------------
            with _timed() as t_parse:
                pdf_content = __import__("mkg.pdf_parser", fromlist=["PDFParser"]).PDFParser().parse(str(cfg.pdf_path))
            if pdf_content is None:
                raise RuntimeError(f"PDFParser.parse() returned None for {cfg.pdf_path}")

            # ---- Stage 2: LLM concept extraction -------------------------
            with _timed() as t_extract:
                llm = init_llm_from_db(db)
                if llm is None:
                    raise RuntimeError(
                        "init_llm_from_db() returned None — no LLM provider "
                        "configured in the test database. Configure one via "
                        "`mkg` CLI before running E2E tests."
                    )
                extracted = LLMConceptExtractor().extract(pdf_content)

            if extracted.concept_tree is None:
                raise RuntimeError("LLM returned no concept_tree")

            # ---- Stage 3: Store paper -----------------------------------
            with _timed() as t_store:
                # LLM may return title/abstract as dict (bilingual {"en":"...","zh":"..."}).
                # Convert to str for DB storage.
                title = extracted.title
                if isinstance(title, dict):
                    title = title.get("en") or title.get("zh") or str(title)
                if not title:
                    title = pdf_content.title

                abstract = extracted.abstract
                if isinstance(abstract, dict):
                    abstract = abstract.get("en") or abstract.get("zh") or str(abstract)
                if not abstract:
                    abstract = pdf_content.abstract

                paper_data = {
                    "doi": cfg.pdf_path.stem,
                    "title": title,
                    "abstract": abstract,
                    "authors": extracted.authors or pdf_content.authors,
                    "pdf_path": str(cfg.pdf_path),
                }
                paper_doi = db.add_paper(paper_data)
                concept_tree_dict = extracted.concept_tree.to_dict()
                db.save_concept_extraction(paper_doi, concept_tree_dict, extracted.raw_response)

            # ---- Stage 4: Build graph ------------------------------------
            with _timed() as t_graph:
                graph = KnowledgeGraph(db)
                graph.build_from_paper(paper_doi, concept_tree_dict)
                graph_stats = graph.get_stats()
                graph_tree = graph.get_tree()
                graph_tree_text = _render_tree_text(graph_tree)

            # ---- Stage 5: Obsidian export --------------------------------
            obsidian_vault_path: Path | None = None
            obsidian_file_count = 0
            export_obsidian_seconds: float | None = None
            if cfg.enable_obsidian:
                with _timed() as t_obs:
                    vault_dir = cfg.work_dir / "vault"
                    exporter = ObsidianExporter(str(vault_dir))
                    # Suppress stdout — ObsidianExporter uses print() with
                    # Unicode chars that may fail on Windows GBK consoles.
                    import sys
                    from io import StringIO
                    old_stdout = sys.stdout
                    sys.stdout = StringIO()
                    try:
                        exporter.export_from_sqlite(db, graph)
                    finally:
                        sys.stdout = old_stdout
                    obsidian_vault_path = vault_dir
                    obsidian_file_count = sum(1 for _ in vault_dir.rglob("*.md"))
                export_obsidian_seconds = t_obs.elapsed

            # ---- Stage 6: Neo4j sync (conditional) -----------------------
            neo4j_stats: dict | None = None
            neo4j_skipped_reason: str | None = None
            sync_neo4j_seconds: float | None = None

            if not cfg.enable_neo4j:
                neo4j_skipped_reason = "disabled"
            else:
                try:
                    from mkg.neo4j_store import Neo4jStore

                    neo4j_store = Neo4jStore()
                    if not neo4j_store.connected:
                        neo4j_skipped_reason = "not_connected"
                    elif not cfg.neo4j_force and not _has_safe_wipe(neo4j_store):
                        neo4j_skipped_reason = "unsafe_no_wipe"
                    else:
                        with _timed() as t_neo4j:
                            if cfg.neo4j_force and _has_safe_wipe(neo4j_store):
                                _safe_wipe(neo4j_store)
                            neo4j_store.sync_all_from_sqlite(db)
                            neo4j_stats = neo4j_store.get_stats()
                        sync_neo4j_seconds = t_neo4j.elapsed
                except Exception as e:  # noqa: BLE001
                    neo4j_skipped_reason = f"error: {type(e).__name__}: {e}"

            return E2EResult(
                config=cfg,
                pdf_content=pdf_content,
                extracted=extracted,
                paper_doi=paper_doi,
                graph_stats=graph_stats,
                graph_tree_text=graph_tree_text,
                obsidian_vault_path=obsidian_vault_path,
                obsidian_file_count=obsidian_file_count,
                neo4j_stats=neo4j_stats,
                neo4j_skipped_reason=neo4j_skipped_reason,
                timings=StageTimings(
                    parse_pdf=t_parse.elapsed,
                    extract_concepts=t_extract.elapsed,
                    store_paper=t_store.elapsed,
                    build_graph=t_graph.elapsed,
                    export_obsidian=export_obsidian_seconds,
                    sync_neo4j=sync_neo4j_seconds,
                ),
                db_path=db_path,
            )
        finally:
            try:
                db.close()
            except Exception:
                pass
            if neo4j_store is not None:
                try:
                    neo4j_store.close()
                except Exception:
                    pass


def _has_safe_wipe(store) -> bool:
    """Return True if Neo4jStore exposes a method we can use to wipe the DB."""
    for name in ("clear_all", "delete_all", "wipe", "reset"):
        if callable(getattr(store, name, None)):
            return True
    return False


def _safe_wipe(store) -> None:
    """Call whichever wipe method the store has. Only reachable if
    `_has_safe_wipe(store)` is True."""
    for name in ("clear_all", "delete_all", "wipe", "reset"):
        fn = getattr(store, name, None)
        if callable(fn):
            fn()
            return
