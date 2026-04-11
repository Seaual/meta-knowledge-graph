# E2E Pipeline Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a shared `E2ERunner` that drives the full mkg pipeline (PDF → LLM → SQLite → KnowledgeGraph → Obsidian → Neo4j) with exactly one live LLM call per invocation, exposed as both a pytest suite (opt-in via `-m e2e`) and a rich CLI script.

**Architecture:** Layered — `tests/e2e/runner.py` holds a pure `E2ERunner` returning an immutable `E2EResult`; `tests/e2e/conftest.py` provides a session-scoped fixture that runs it once; `tests/e2e/test_pipeline.py` contains 16 assertion functions that read the shared result; `scripts/e2e_test.py` is a typer CLI that imports the runner and renders a rich progress table.

**Tech Stack:** Python 3.11+, pytest, typer, rich, dataclasses (frozen). No new dependencies. Real targets: `mkg.pdf_parser.PDFParser`, `mkg.concept_extractor.LLMConceptExtractor`, `mkg.database.Database`, `mkg.graph.KnowledgeGraph`, `mkg.obsidian_exporter.ObsidianExporter`, `mkg.neo4j_store.Neo4jStore`, `mkg.llm.init_llm_from_db`.

**Reference spec:** `docs/superpowers/specs/2026-04-11-e2e-pipeline-test-design.md`

**Key real-codebase facts (verified during planning):**
- `PDFParser.parse(pdf_path: str) -> PaperContent | None` — can return None, caller must check.
- `LLMConceptExtractor.extract(paper_content: PaperContent, existing_concepts: str = "") -> LLMExtractedContent` — takes `PaperContent`, returns `LLMExtractedContent` (both from `mkg.pdf_models`).
- `LLMExtractedContent.concept_tree` is a `ConceptTree` dataclass; use `.to_dict()` to get a dict for downstream calls.
- `Database.add_paper(paper_data: dict) -> str` — returns the stored DOI.
- `Database.save_concept_extraction(paper_doi, hierarchy: dict, raw_response: str)` — takes dict, not object.
- `KnowledgeGraph.build_from_paper(paper_doi: str, concept_tree: dict)` — takes dict.
- `KnowledgeGraph.get_tree(root_concept=None, view="knowledge") -> rich.tree.Tree` — returns a rich `Tree` object, NOT a string. To convert to text, render through `rich.console.Console` with `file=StringIO()`.
- `ObsidianExporter(vault_path: str)` — creates `vault_path/{Papers,Concepts,Maps}` in `__init__`. `export_from_sqlite(db, graph, output_name="mkg_knowledge")` prints to stdout as a side-effect.
- `Neo4jStore(uri=None, user=None, password=None)` — reads env vars when args are None. `.connected: bool` indicates whether the bolt session succeeded. `close()` is idempotent. **No `clear_all` / `wipe` / `delete_all` method exists.**
- `init_llm_from_db(db) -> BaseChatModel | None` — returns None if no LLM config saved in db. Runner must raise a clear error in that case.

---

## File Structure

| File | Responsibility |
|---|---|
| `tests/fixtures/e2e_sample.pdf` | Canonical input PDF (copy of `papers/pending/2305.11738v4_1774912147.pdf`, 1.5 MB) |
| `tests/e2e/__init__.py` | Empty — marks package |
| `tests/e2e/fixture_metadata.py` | `FIXTURE_PDF_NAME`, `FIXTURE_EXPECTED_DOI`, `FIXTURE_TOPIC_KEYWORDS` |
| `tests/e2e/runner.py` | `E2EConfig`, `StageTimings`, `E2EResult`, `E2ERunner` + internal helpers (`_validate_work_dir`, `_timed`, `_render_tree_text`) |
| `tests/e2e/conftest.py` | Session-scoped `e2e_result` fixture |
| `tests/e2e/test_pipeline.py` | 16 assertion functions, all `pytestmark = pytest.mark.e2e` |
| `scripts/e2e_test.py` | Typer CLI wrapping the runner with rich output |
| `pyproject.toml` | Add `e2e` marker + `addopts = "-m 'not e2e'"` |

---

## Task 1: Project scaffolding (marker, package, fixture metadata)

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/fixtures/e2e_sample.pdf` (binary copy)
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/fixture_metadata.py`

- [ ] **Step 1: Copy the canonical fixture PDF**

```bash
mkdir -p tests/fixtures
cp "papers/pending/2305.11738v4_1774912147.pdf" tests/fixtures/e2e_sample.pdf
ls -la tests/fixtures/e2e_sample.pdf
```

Expected: file exists, ~1.5 MB.

- [ ] **Step 2: Create the empty e2e package**

```bash
mkdir -p tests/e2e
touch tests/e2e/__init__.py
```

- [ ] **Step 3: Create `tests/e2e/fixture_metadata.py`**

```python
"""Metadata for the canonical E2E test fixture.

Everything in this file is keyed to `tests/fixtures/e2e_sample.pdf`. If that
file is replaced, update the constants below — nothing else in the E2E suite
references the specific paper.
"""

from pathlib import Path

FIXTURE_PDF_PATH = Path(__file__).parent.parent / "fixtures" / "e2e_sample.pdf"
FIXTURE_PDF_NAME = "e2e_sample.pdf"
FIXTURE_EXPECTED_DOI = "e2e_sample"  # Database.add_paper uses pdf_path.stem

# Loose keyword set for "did the LLM return something topically relevant"
# assertions. Matched case-insensitively via `any(kw in text.lower() ...)`.
# Initial values target 2305.11738v4 (CRITIC: LLMs Self-Correct with
# Tool-Interactive Critiquing). If false positives occur, GROW this set —
# never loosen the count thresholds in test_pipeline.py.
FIXTURE_TOPIC_KEYWORDS: frozenset[str] = frozenset({
    "llm",
    "language model",
    "critic",
    "correct",
    "tool",
    "feedback",
    "reason",
    "reasoning",
    "evaluation",
    "大语言模型",
    "自我修正",
    "工具",
})
```

- [ ] **Step 4: Add pytest marker and default skip to `pyproject.toml`**

Read the current `[tool.pytest.ini_options]` section first (it may not exist). If it doesn't exist, add it. If it does, add the two keys — do not clobber existing keys.

Desired final state of the section (merge with any existing keys):

```toml
[tool.pytest.ini_options]
markers = [
    "e2e: end-to-end pipeline test with real LLM (slow, costs money, opt-in via -m e2e)",
]
addopts = "-m 'not e2e'"
```

- [ ] **Step 5: Verify marker is registered and default-skipped**

```bash
pytest --collect-only -q 2>&1 | tail -5
```

Expected: existing tests collected, zero E2E tests (since `tests/e2e/` has no test files yet), no "unknown marker" warnings.

```bash
pytest --markers 2>&1 | grep e2e
```

Expected: `@pytest.mark.e2e: end-to-end pipeline test with real LLM...`

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/e2e_sample.pdf tests/e2e/__init__.py tests/e2e/fixture_metadata.py pyproject.toml
git commit -m "test(e2e): add fixture, e2e package, and pytest marker"
```

---

## Task 2: Runner data types (frozen dataclasses)

**Files:**
- Create: `tests/e2e/runner.py` (types only; `E2ERunner` class stub added later)
- Create: `tests/e2e/test_runner_types.py`

- [ ] **Step 1: Write failing test for the three dataclasses**

Create `tests/e2e/test_runner_types.py`:

```python
"""Unit tests for runner.py dataclasses (do NOT need live LLM).

These are NOT marked e2e — they run in the default test suite.
"""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from tests.e2e.runner import E2EConfig, E2EResult, StageTimings


def test_e2e_config_has_expected_fields(tmp_path):
    cfg = E2EConfig(
        pdf_path=tmp_path / "x.pdf",
        work_dir=tmp_path / "work",
    )
    assert cfg.pdf_path == tmp_path / "x.pdf"
    assert cfg.enable_neo4j is True
    assert cfg.enable_obsidian is True
    assert cfg.keep_artifacts is False
    assert cfg.neo4j_force is False


def test_e2e_config_is_frozen(tmp_path):
    cfg = E2EConfig(pdf_path=tmp_path / "x.pdf", work_dir=tmp_path / "work")
    with pytest.raises(FrozenInstanceError):
        cfg.enable_neo4j = False  # type: ignore[misc]


def test_stage_timings_allows_optional_stages():
    t = StageTimings(
        parse_pdf=0.1,
        extract_concepts=1.0,
        store_paper=0.01,
        build_graph=0.02,
        export_obsidian=None,
        sync_neo4j=None,
    )
    assert t.export_obsidian is None


def test_e2e_result_is_frozen(tmp_path):
    cfg = E2EConfig(pdf_path=tmp_path / "x.pdf", work_dir=tmp_path / "work")
    t = StageTimings(0.1, 1.0, 0.01, 0.02, None, None)
    result = E2EResult(
        config=cfg,
        pdf_content=None,
        extracted=None,
        paper_doi="",
        graph_stats={},
        graph_tree_text="",
        obsidian_vault_path=None,
        obsidian_file_count=0,
        neo4j_stats=None,
        neo4j_skipped_reason="disabled",
        timings=t,
        db_path=Path("/tmp/fake.db"),
    )
    with pytest.raises(FrozenInstanceError):
        result.paper_doi = "other"  # type: ignore[misc]
```

- [ ] **Step 2: Run the test to confirm it fails with ImportError**

```bash
pytest tests/e2e/test_runner_types.py -v
```

Expected: `ModuleNotFoundError: No module named 'tests.e2e.runner'` or similar.

- [ ] **Step 3: Create `tests/e2e/runner.py` with just the dataclasses**

```python
"""E2E pipeline runner.

Drives the full mkg pipeline: PDF → LLM → SQLite → KnowledgeGraph →
Obsidian → Neo4j. Pure logic, no asserts, no rich output. Callers decide how
to display results.

See docs/superpowers/specs/2026-04-11-e2e-pipeline-test-design.md for the
full design.
"""

from __future__ import annotations

from dataclasses import dataclass
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
```

Note: `pdf_content` and `extracted` are typed `Any` to avoid importing heavy mkg modules at dataclass-definition time. The runner implementation (Task 5) will populate them with real `PaperContent` / `LLMExtractedContent` instances.

- [ ] **Step 4: Run the test and confirm it passes**

```bash
pytest tests/e2e/test_runner_types.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/runner.py tests/e2e/test_runner_types.py
git commit -m "test(e2e): add runner dataclasses (E2EConfig, StageTimings, E2EResult)"
```

---

## Task 3: Runner work_dir safety validation

**Files:**
- Modify: `tests/e2e/runner.py`
- Create: `tests/e2e/test_runner_validation.py`

- [ ] **Step 1: Write failing tests for `_validate_work_dir`**

Create `tests/e2e/test_runner_validation.py`:

```python
"""Tests for runner safety validation (no live LLM required)."""

from pathlib import Path

import pytest

from tests.e2e.runner import _validate_work_dir


def test_accepts_fresh_tmp_path(tmp_path):
    target = tmp_path / "fresh"
    _validate_work_dir(target)  # Should not raise; does NOT create the dir.


def test_accepts_empty_existing_tmp_path(tmp_path):
    target = tmp_path / "empty"
    target.mkdir()
    _validate_work_dir(target)  # empty existing dir is OK


def test_rejects_nonempty_existing_dir(tmp_path):
    target = tmp_path / "nonempty"
    target.mkdir()
    (target / "file.txt").write_text("x")
    with pytest.raises(ValueError, match="not empty"):
        _validate_work_dir(target)


def test_rejects_project_root(tmp_path, monkeypatch):
    # Simulate work_dir pointing at the repo root by passing a path whose
    # resolved form is the repo root.
    repo_root = Path(__file__).resolve().parents[2]
    with pytest.raises(ValueError, match="project root"):
        _validate_work_dir(repo_root)


def test_rejects_backend_subtree(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    backend_child = repo_root / "backend" / "oops"
    with pytest.raises(ValueError, match="backend"):
        _validate_work_dir(backend_child)
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/e2e/test_runner_validation.py -v
```

Expected: `ImportError: cannot import name '_validate_work_dir'`.

- [ ] **Step 3: Implement `_validate_work_dir` in `tests/e2e/runner.py`**

Add at the bottom of `tests/e2e/runner.py`:

```python
# ---- Safety helpers ----------------------------------------------------


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
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
pytest tests/e2e/test_runner_validation.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/runner.py tests/e2e/test_runner_validation.py
git commit -m "test(e2e): add work_dir safety validation"
```

---

## Task 4: Runner helpers — `_timed` context manager and `_render_tree_text`

**Files:**
- Modify: `tests/e2e/runner.py`
- Create: `tests/e2e/test_runner_helpers.py`

- [ ] **Step 1: Write failing tests**

Create `tests/e2e/test_runner_helpers.py`:

```python
"""Tests for runner helpers (no live LLM required)."""

import time

from rich.tree import Tree

from tests.e2e.runner import _render_tree_text, _timed


def test_timed_measures_elapsed():
    with _timed() as t:
        time.sleep(0.02)
    assert t.elapsed >= 0.02
    assert t.elapsed < 1.0


def test_timed_records_on_exception():
    try:
        with _timed() as t:
            time.sleep(0.01)
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert t.elapsed >= 0.01


def test_render_tree_text_empty_tree():
    tree = Tree("root")
    text = _render_tree_text(tree)
    assert "root" in text
    assert isinstance(text, str)


def test_render_tree_text_with_children():
    tree = Tree("parent")
    tree.add("child-a")
    tree.add("child-b")
    text = _render_tree_text(tree)
    assert "parent" in text
    assert "child-a" in text
    assert "child-b" in text
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/e2e/test_runner_helpers.py -v
```

Expected: ImportError on `_timed` / `_render_tree_text`.

- [ ] **Step 3: Implement the helpers in `tests/e2e/runner.py`**

Add these imports at the top of `runner.py`:

```python
import time
from contextlib import contextmanager
from dataclasses import field
from io import StringIO
```

Add these helpers at the bottom of `runner.py`:

```python
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
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
pytest tests/e2e/test_runner_helpers.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/runner.py tests/e2e/test_runner_helpers.py
git commit -m "test(e2e): add _timed context manager and _render_tree_text helper"
```

---

## Task 5: `E2ERunner.run()` — full 6-stage pipeline

**Files:**
- Modify: `tests/e2e/runner.py`

This task introduces the one piece that cannot be TDD'd cheaply: the method that actually makes the live LLM call. Verification of this task is a single manual smoke-test run at Step 6. The real test suite for `run()` is Task 7 (the 16 assertion functions).

- [ ] **Step 1: Add the `E2ERunner` class to `tests/e2e/runner.py`**

Append after the existing helpers. All imports already added.

```python
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
        from mkg.pdf_parser import PDFParser

        cfg = self.config
        cfg.work_dir.mkdir(parents=True, exist_ok=True)
        db_path = cfg.work_dir / "mkg.db"

        db = Database(str(db_path))
        db.connect()
        neo4j_store = None

        try:
            # ---- Stage 1: Parse PDF --------------------------------------
            with _timed() as t_parse:
                pdf_content = PDFParser().parse(str(cfg.pdf_path))
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
                # Propagate — assertion layer will turn this into a clear failure.
                raise RuntimeError("LLM returned no concept_tree")

            # ---- Stage 3: Store paper -----------------------------------
            with _timed() as t_store:
                paper_data = {
                    "doi": cfg.pdf_path.stem,
                    "title": extracted.title or pdf_content.title,
                    "abstract": extracted.abstract or pdf_content.abstract,
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
                    exporter.export_from_sqlite(db, graph)
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
                except Exception as e:  # noqa: BLE001 — Neo4j errors become skip reasons
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
    """Return True if Neo4jStore exposes a method we can use to wipe the DB.

    As of planning, no such method exists. This function is a forward-
    looking shim — if someone adds `clear_all`, `delete_all`, or `wipe`,
    Stage 6 will start running automatically in default mode.
    """
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
```

- [ ] **Step 2: Run existing unit tests to confirm nothing broke**

```bash
pytest tests/e2e/test_runner_types.py tests/e2e/test_runner_validation.py tests/e2e/test_runner_helpers.py -v
```

Expected: all 13 tests pass (no regressions).

- [ ] **Step 3: Pre-flight — confirm LLM is configured in the mkg db**

This runner uses `init_llm_from_db` which reads LLM config from the mkg SQLite DB. Before running a real E2E smoke test, an LLM provider must be saved. Check the project DB first:

```bash
python -c "from mkg.database import Database; db = Database('backend/mkg.db'); db.connect(); print(db.get_llm_config())"
```

Expected: non-empty dict with at least one provider. If empty, configure via the backend API or `mkg` CLI before continuing. **Do not write any fallback/mock here — the whole point of this test is real LLM.**

- [ ] **Step 4: Seed LLM config into an isolated test database**

Because `init_llm_from_db` reads from the DB we just created in `cfg.work_dir`, the isolated test DB starts empty with no LLM config. We need the runner to use the real LLM config without touching the project DB. The cleanest solution: seed the test DB from the project DB at runner startup.

Modify `E2ERunner.__init__` to accept an optional `llm_config_source_db: Path | None = None` and, if provided, copy the LLM config rows before `run()` proceeds. Update `E2EConfig`:

```python
@dataclass(frozen=True)
class E2EConfig:
    pdf_path: Path
    work_dir: Path
    enable_neo4j: bool = True
    enable_obsidian: bool = True
    keep_artifacts: bool = False
    neo4j_force: bool = False
    llm_config_source_db: Path | None = None  # copy LLM config from here if set
```

Add this helper at the top of `E2ERunner.run()`, right after `db.connect()`:

```python
            if cfg.llm_config_source_db is not None:
                _copy_llm_config(src=cfg.llm_config_source_db, dst=db)
```

And this module-level helper at the bottom of `runner.py`:

```python
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
```

- [ ] **Step 5: Extend `test_e2e_config_has_expected_fields` to cover the new field, then verify**

Add one line inside the existing test in `tests/e2e/test_runner_types.py`:

```python
    assert cfg.llm_config_source_db is None
```

Run the unit tests:

```bash
pytest tests/e2e/test_runner_types.py tests/e2e/test_runner_validation.py tests/e2e/test_runner_helpers.py -v
```

Expected: all green.

- [ ] **Step 6: Manual smoke test — run the runner once against the real fixture**

This is the one expensive step: ~$0.10 and ~30-60 seconds of real LLM time. Run via a throwaway Python one-liner (we'll wrap this properly in Task 8):

```bash
python -c "
import tempfile
from pathlib import Path
from tests.e2e.runner import E2EConfig, E2ERunner
from tests.e2e.fixture_metadata import FIXTURE_PDF_PATH

work_dir = Path(tempfile.mkdtemp(prefix='mkg-e2e-smoke-'))
cfg = E2EConfig(
    pdf_path=FIXTURE_PDF_PATH,
    work_dir=work_dir,
    enable_neo4j=False,  # skip Neo4j for the smoke test
    llm_config_source_db=Path('backend/mkg.db'),
)
result = E2ERunner(cfg).run()
print('paper_doi:', result.paper_doi)
print('concepts:', result.graph_stats.get('concepts', {}).get('total'))
print('obsidian files:', result.obsidian_file_count)
print('root concept:', result.extracted.concept_tree.concept)
print('timings:', result.timings)
"
```

Expected: completes without exception; prints a paper_doi of `e2e_sample`, a nonzero concept count, a nonzero obsidian file count, a non-empty root concept, and positive timings for stages 1-5.

If it fails, do NOT hack around the failure — read the traceback, fix the root cause in the runner, and re-run. Common causes:
- `init_llm_from_db` returned None → LLM not seeded; check Step 4 helper.
- `PDFParser.parse` returned None → fixture PDF unreadable; re-check the copy in Task 1 Step 1.
- Schema mismatch in `_copy_llm_config` → method names in mkg.database don't match; adjust.

- [ ] **Step 7: Commit**

```bash
git add tests/e2e/runner.py tests/e2e/test_runner_types.py
git commit -m "feat(e2e): implement E2ERunner.run() for full 6-stage pipeline"
```

---

## Task 6: Session fixture in `tests/e2e/conftest.py`

**Files:**
- Create: `tests/e2e/conftest.py`

- [ ] **Step 1: Write `conftest.py`**

```python
"""Session-scoped fixture that runs the E2E pipeline exactly once per session.

All `test_*` functions in `tests/e2e/test_pipeline.py` share this single
result to keep LLM costs to one call per `pytest -m e2e` invocation.
"""

from pathlib import Path

import pytest

from tests.e2e.fixture_metadata import FIXTURE_PDF_PATH
from tests.e2e.runner import E2EConfig, E2EResult, E2ERunner

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PROJECT_DB = _PROJECT_ROOT / "backend" / "mkg.db"


@pytest.fixture(scope="session")
def e2e_result(tmp_path_factory) -> E2EResult:
    """Run the full pipeline once, share the result across every e2e test."""
    work_dir = tmp_path_factory.mktemp("e2e")
    # tmp_path_factory yields an existing empty dir; our runner accepts that.
    config = E2EConfig(
        pdf_path=FIXTURE_PDF_PATH,
        work_dir=work_dir,
        enable_neo4j=True,  # will likely skip with unsafe_no_wipe / not_connected
        enable_obsidian=True,
        llm_config_source_db=_PROJECT_DB if _PROJECT_DB.exists() else None,
    )
    return E2ERunner(config).run()
```

- [ ] **Step 2: Commit (cannot test yet — assertions come next)**

```bash
git add tests/e2e/conftest.py
git commit -m "test(e2e): add session-scoped e2e_result fixture"
```

---

## Task 7: Assertion functions in `tests/e2e/test_pipeline.py`

**Files:**
- Create: `tests/e2e/test_pipeline.py`

This is the real test suite for the runner. Because it's opt-in via `-m e2e`, it won't run in the default suite.

- [ ] **Step 1: Write all 16 test functions**

Create `tests/e2e/test_pipeline.py`:

```python
"""End-to-end pipeline assertions.

Opt-in via `pytest -m e2e`. Shares a single session-scoped result from the
`e2e_result` fixture so exactly one live LLM call happens per pytest run.

Assertion strategy (from spec § 5): structural assertions first, then loose
keyword matching for "did the LLM return topically relevant content".
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e.fixture_metadata import FIXTURE_EXPECTED_DOI, FIXTURE_TOPIC_KEYWORDS
from tests.e2e.runner import E2EResult

pytestmark = pytest.mark.e2e


# ---- Helpers -----------------------------------------------------------


def _hits_any_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(kw.lower() in lowered for kw in FIXTURE_TOPIC_KEYWORDS)


def _count_keyword_hits(text: str) -> int:
    lowered = text.lower()
    return sum(1 for kw in FIXTURE_TOPIC_KEYWORDS if kw.lower() in lowered)


def _flatten_concept_children(tree) -> list[str]:
    """Return direct + grandchild concept names of a ConceptTree."""
    out: list[str] = []
    for child in getattr(tree, "children", []) or []:
        out.append(child.concept)
        for grandchild in getattr(child, "children", []) or []:
            out.append(grandchild.concept)
    return out


# ---- Structural assertions (13) ---------------------------------------


def test_pdf_parsed(e2e_result: E2EResult) -> None:
    assert e2e_result.pdf_content is not None
    assert len(e2e_result.pdf_content.full_text) > 500


def test_pdf_has_title(e2e_result: E2EResult) -> None:
    assert isinstance(e2e_result.pdf_content.title, str)
    assert e2e_result.pdf_content.title.strip() != ""


def test_extraction_returned(e2e_result: E2EResult) -> None:
    assert e2e_result.extracted is not None
    assert e2e_result.extracted.concept_tree is not None


def test_concept_tree_has_root(e2e_result: E2EResult) -> None:
    root_text = e2e_result.extracted.concept_tree.concept
    assert isinstance(root_text, str)
    assert root_text.strip() != ""


def test_concept_tree_has_children(e2e_result: E2EResult) -> None:
    assert len(e2e_result.extracted.concept_tree.children) >= 1


def test_research_questions_nonempty(e2e_result: E2EResult) -> None:
    assert len(e2e_result.extracted.research_questions) >= 1


def test_paper_stored(e2e_result: E2EResult) -> None:
    assert e2e_result.paper_doi == FIXTURE_EXPECTED_DOI

    from mkg.database import Database

    db = Database(str(e2e_result.db_path))
    db.connect()
    try:
        row = db.get_paper(FIXTURE_EXPECTED_DOI)
    finally:
        db.close()
    assert row is not None
    assert row["doi"] == FIXTURE_EXPECTED_DOI


def test_graph_has_concepts(e2e_result: E2EResult) -> None:
    total = e2e_result.graph_stats.get("concepts", {}).get("total", 0)
    assert total > 0, f"expected concepts in graph, got {e2e_result.graph_stats}"


def test_graph_has_relations(e2e_result: E2EResult) -> None:
    relations = e2e_result.graph_stats.get("relations", 0)
    assert relations > 0, f"expected relations in graph, got {e2e_result.graph_stats}"


def test_graph_tree_renderable(e2e_result: E2EResult) -> None:
    assert isinstance(e2e_result.graph_tree_text, str)
    assert len(e2e_result.graph_tree_text) > 0


def test_obsidian_vault_exported(e2e_result: E2EResult) -> None:
    assert e2e_result.obsidian_vault_path is not None
    assert e2e_result.obsidian_vault_path.exists()
    assert e2e_result.obsidian_file_count >= 1


def test_obsidian_has_paper_note(e2e_result: E2EResult) -> None:
    vault = e2e_result.obsidian_vault_path
    assert vault is not None
    title = e2e_result.extracted.title or e2e_result.pdf_content.title
    doi = e2e_result.paper_doi

    found = False
    for md in vault.rglob("*.md"):
        content = md.read_text(encoding="utf-8", errors="ignore")
        if title and title in content:
            found = True
            break
        if doi in content:
            found = True
            break
    assert found, f"no vault .md contained title={title!r} or doi={doi!r}"


def test_neo4j_sync_or_skip(e2e_result: E2EResult) -> None:
    if e2e_result.neo4j_skipped_reason:
        pytest.skip(f"neo4j skipped: {e2e_result.neo4j_skipped_reason}")
    assert e2e_result.neo4j_stats is not None
    assert e2e_result.neo4j_stats.get("total_concepts", 0) > 0


# ---- Loose keyword matching (3) ---------------------------------------


def test_root_concept_topic_relevant(e2e_result: E2EResult) -> None:
    root_text = e2e_result.extracted.concept_tree.concept
    assert _hits_any_keyword(root_text), (
        f"root concept {root_text!r} did not hit any topic keyword; "
        f"grow FIXTURE_TOPIC_KEYWORDS in fixture_metadata.py if legit"
    )


def test_any_child_topic_relevant(e2e_result: E2EResult) -> None:
    children = _flatten_concept_children(e2e_result.extracted.concept_tree)
    assert children, "concept tree had no children to match against"
    assert any(_hits_any_keyword(c) for c in children), (
        f"no child/grandchild concept hit topic keywords; children={children}"
    )


def test_research_questions_topic_relevant(e2e_result: E2EResult) -> None:
    questions = e2e_result.extracted.research_questions
    joined = " ".join(questions)
    hits = _count_keyword_hits(joined)
    assert hits >= 2, (
        f"research questions joined text only hit {hits} keyword(s); "
        f"questions={questions}"
    )
```

- [ ] **Step 2: Run the E2E suite against the real pipeline**

This is the second (and main) expensive run. Estimated cost: ~$0.10, ~30-60s.

```bash
pytest tests/e2e/test_pipeline.py -m e2e -v
```

Expected: 15 passed, 1 skipped (the Neo4j test, likely `unsafe_no_wipe` or `not_connected`). If any assertion fails, the failure message tells you which facet of the pipeline is broken. Do NOT loosen an assertion to make it pass — diagnose the root cause.

- [ ] **Step 3: Confirm the default suite still skips E2E**

```bash
pytest -q 2>&1 | tail -5
```

Expected: all pre-existing tests plus the runner unit tests (`test_runner_types`, `test_runner_validation`, `test_runner_helpers`) pass; nothing under `tests/e2e/test_pipeline.py` runs.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_pipeline.py
git commit -m "test(e2e): add 16 pipeline assertions (structural + keyword matching)"
```

---

## Task 8: `scripts/e2e_test.py` — typer CLI with rich output

**Files:**
- Create: `scripts/e2e_test.py`

- [ ] **Step 1: Write the script**

```python
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
    console.print("[yellow]⚠ Running with live LLM. Est. cost ~$0.10, ~30-60s[/yellow]")

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
    console.print(f"[green]✓ E2E pipeline completed in {total:.2f}s[/green]")

    if keep_artifacts:
        console.print(f"[dim]Artifacts kept at: {work_dir}[/dim]")


if __name__ == "__main__":
    app()
```

- [ ] **Step 2: Run the script with `--no-neo4j` to keep it fast**

Third and final expensive run (~$0.10, ~30-60s):

```bash
python scripts/e2e_test.py --no-neo4j
```

Expected: rich summary table, `✓ E2E pipeline completed in X.XXs`, exit code 0.

```bash
echo $?
```

Expected: `0`.

- [ ] **Step 3: Test the failure path with a bogus PDF**

```bash
python scripts/e2e_test.py --pdf /nonexistent.pdf --no-neo4j 2>&1 | tail -5
echo $?
```

Expected: red error output, exit code `1`.

- [ ] **Step 4: Commit**

```bash
git add scripts/e2e_test.py
git commit -m "feat(e2e): add scripts/e2e_test.py — typer CLI for the pipeline runner"
```

---

## Task 9: Final verification — full default suite still clean, E2E runs on demand

**Files:**
- None modified (verification only)

- [ ] **Step 1: Default suite — confirm nothing E2E runs**

```bash
pytest -q 2>&1 | tail -10
```

Expected: all pre-existing tests pass. `test_runner_types`, `test_runner_validation`, `test_runner_helpers` all included in the count. Zero tests from `tests/e2e/test_pipeline.py` run.

- [ ] **Step 2: Explicit E2E run — all 16 assertions reachable**

```bash
pytest tests/e2e/test_pipeline.py -m e2e -v 2>&1 | tail -25
```

Expected: 15 passed, 1 skipped (`test_neo4j_sync_or_skip`), no failures.

- [ ] **Step 3: Use GitNexus to verify scope**

```bash
# This project uses GitNexus per CLAUDE.md. Verify changes match expectations.
```

Run the `gitnexus_detect_changes` tool and confirm the changed symbols match exactly what this plan touches: new files under `tests/e2e/`, `tests/fixtures/e2e_sample.pdf`, `scripts/e2e_test.py`, and `pyproject.toml`. No other files should be listed. If anything unexpected shows up, investigate before the final push.

- [ ] **Step 4: Run the script one more time end-to-end, with Obsidian + default Neo4j behavior**

```bash
python scripts/e2e_test.py
```

Expected: table with Neo4j row showing `unsafe_no_wipe` or `not_connected`, everything else green. Exit 0.

- [ ] **Step 5: Refresh the GitNexus index after commits**

```bash
npx gitnexus analyze --embeddings
```

Expected: index refresh completes without errors.

---

## Scope Coverage Check

Every section of the spec maps to a task:

| Spec section | Covered by |
|---|---|
| Directory layout | Task 1 |
| Core types (`E2EConfig`, `StageTimings`, `E2EResult`) | Task 2 |
| Data flow (6 stages) | Task 5 |
| Error handling & Neo4j conditional | Task 5 (stage 6 + `_has_safe_wipe`) |
| Work dir lifecycle + safety | Task 3 (validation) + Task 5 (creation) + Task 8 (script cleanup) |
| External state pollution (LLM cost warning, Neo4j safe mode) | Task 5 + Task 8 |
| Structural assertions (13) | Task 7 |
| Loose keyword matching (3) | Task 7 |
| Script output (rich table) | Task 8 |
| pytest markers / addopts | Task 1 |
| conftest fixture | Task 6 |
| CLI options | Task 8 |
| Fixture file management | Task 1 |

No unmapped spec sections.

---

## Deviations from Spec

1. **`E2EConfig` gained a `llm_config_source_db` field.** The spec did not specify where the isolated test DB gets its LLM provider config from; leaving it unset would cause `init_llm_from_db` to return None and crash stage 2. Solution: copy LLM config from the real project DB at runner startup.

2. **`E2EConfig` gained a `neo4j_force` field.** The spec mentioned `--neo4j-force` as a CLI flag but didn't show it in the `E2EConfig` dataclass. Promoted to a first-class config field so the pytest fixture can control it too if ever needed.

3. **`pdf_content` and `extracted` are typed `Any` on `E2EResult`.** The spec used `PaperContent` / `LLMExtractedContent`. Typing them concretely would force the dataclass to import `mkg.pdf_models` at import time, which is fine in itself but couples `tests/e2e/runner.py` to a specific import path. The runner populates them with real objects at runtime; type-checkers can add ignores if this becomes annoying later.
