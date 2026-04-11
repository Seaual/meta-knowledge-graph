# E2E Pipeline Test — Design

**Date**: 2026-04-11
**Status**: Approved, pending implementation plan
**Scope**: A runnable end-to-end test program that exercises the full mkg pipeline: PDF → LLM concept extraction → SQLite → KnowledgeGraph → Obsidian export → Neo4j sync.

## Goal

Build a single source of truth for "does the whole pipeline still work end-to-end" that can be invoked in two forms:

1. **pytest suite** (`tests/e2e/test_pipeline.py`) — granular assertions, opt-in via `-m e2e` marker, default skipped.
2. **Standalone script** (`scripts/e2e_test.py`) — rich CLI with progress table, intended for manual verification and demo.

Both forms share a single `E2ERunner` that makes exactly one real LLM call per invocation.

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| LLM calls | Real, live API calls (no mocks, no replay) |
| Run form | Both pytest suite AND standalone script |
| Coverage | Full pipeline including Obsidian export and Neo4j sync (Neo4j conditional) |
| Test input | Fixed canonical PDF fixture at `tests/fixtures/e2e_sample.pdf` |
| Assertion style | Structural assertions + loose keyword matching |
| Architecture | Shared `E2ERunner` library + session-scoped pytest fixture |

## Non-Goals

- Replay mode / VCR fixtures — not in scope. If the live approach proves too expensive, revisit.
- CI integration — not in default CI. Leave room for a manual `workflow_dispatch` later.
- Performance benchmarks — timings are captured and displayed but not asserted.
- Fuzzing or property-based testing — out of scope.

## Architecture

### Directory Layout

```
tests/
  e2e/
    __init__.py
    runner.py             # E2ERunner + E2EResult + E2EConfig (pure logic)
    conftest.py           # session-scoped fixture: runs runner once
    test_pipeline.py      # 16 assertion functions
    fixture_metadata.py   # FIXTURE_EXPECTED_DOI, FIXTURE_TOPIC_KEYWORDS
  fixtures/
    e2e_sample.pdf        # copied from papers/pending/2305.11738v4_1774912147.pdf
scripts/
  e2e_test.py             # typer CLI: rich progress + output table
pyproject.toml            # adds [tool.pytest.ini_options] markers + addopts
```

### Layer Responsibilities

- **`runner.py`** — the only place that drives the pipeline. Takes `E2EConfig`, returns immutable `E2EResult`. No asserts, no rich printing. Pure function-like.
- **`conftest.py`** — session-scoped `e2e_result` fixture calls `E2ERunner.run()` once and caches the result.
- **`test_pipeline.py`** — 16 `test_*` functions, each asserting one facet of `e2e_result`. Zero IO inside test bodies.
- **`scripts/e2e_test.py`** — builds `E2EConfig` from CLI args, invokes runner, displays rich progress/table, sets exit code.
- **`fixture_metadata.py`** — expected DOI and topic keyword set; decouples assertions from which PDF happens to be the fixture.

### Key Invariant

pytest and the script produce **one** live LLM call per invocation. No duplication.

## Core Types

All in `tests/e2e/runner.py`, all `@dataclass(frozen=True)`:

```python
@dataclass(frozen=True)
class E2EConfig:
    pdf_path: Path
    work_dir: Path
    enable_neo4j: bool = True
    enable_obsidian: bool = True
    keep_artifacts: bool = False

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
    pdf_content: PDFContent                  # from mkg.pdf_models
    extracted: ExtractedConcepts             # from mkg.concept_extractor
    paper_doi: str
    graph_stats: dict
    graph_tree_text: str
    obsidian_vault_path: Path | None
    obsidian_file_count: int
    neo4j_stats: dict | None
    neo4j_skipped_reason: str | None
    timings: StageTimings
    db_path: Path

class E2ERunner:
    def __init__(self, config: E2EConfig): ...
    def run(self) -> E2EResult: ...
```

## Data Flow (6 Stages)

Each stage is timed with `time.perf_counter()` and recorded in `StageTimings`.

| # | Stage | Call | Written to E2EResult |
|---|---|---|---|
| 1 | Parse PDF | `PDFParser().parse(config.pdf_path)` | `pdf_content` |
| 2 | LLM extraction | `init_llm_from_db(db)` → `LLMConceptExtractor().extract(pdf_content)` | `extracted` |
| 3 | Store paper | `db.add_paper({doi: pdf.stem, title, abstract, authors, pdf_path})` + `db.save_concept_extraction(doi, tree, raw)` | `paper_doi` |
| 4 | Build graph | `KnowledgeGraph(db).build_from_paper(doi, tree)` + `graph.get_stats()` + `graph.get_tree()` | `graph_stats`, `graph_tree_text` |
| 5 | Obsidian export | `ObsidianExporter(work_dir/"vault").export_from_sqlite(db, graph)` + `.md` count | `obsidian_vault_path`, `obsidian_file_count` |
| 6 | Neo4j sync (conditional) | `Neo4jStore()` → `.connected` → `sync_all_from_sqlite(db)` → `get_stats()` | `neo4j_stats` OR `neo4j_skipped_reason` |

### Stage Details

- **Stage 2**: `init_llm_from_db(db)` must run before any extractor call (mirrors `cli.py:93`).
- **Stage 3**: DOI is `pdf_path.stem` (mirrors `cli.py:128`). For the canonical fixture this is `"e2e_sample"`.
- **Stage 5**: Vault at `config.work_dir / "vault"` — never touches the repo's `obsidian_vault/`.
- **Stage 6** — Neo4j has four possible states:
  - `enable_neo4j=False` → `neo4j_skipped_reason="disabled"`
  - Connected but no safe wipe method available → `neo4j_skipped_reason="unsafe_no_wipe"` (unless `--neo4j-force`)
  - Not connected → `neo4j_skipped_reason="not_connected"`
  - Connected + wiped + synced → `neo4j_stats = store.get_stats()`, `neo4j_skipped_reason=None`
  - Always `store.close()` in `finally`.

### Risk Acknowledged

If `extracted.concept_tree is None` (LLM returned but JSON parse failed), stage 4 will crash. The runner does NOT pre-check — it lets the crash propagate so the assertion layer sees the real failure mode.

## Error Handling, Cleanup, Isolation

### Runner Exceptions

- Stages 1–5: exceptions **propagate**. Caller decides how to display them.
- Stage 6: exceptions are **caught** and converted into `neo4j_skipped_reason=f"error: {e}"`. "Neo4j not installed" is not an E2E failure.
- `db.close()` and `neo4j_store.close()` always run in `finally`.

### Work Directory Lifecycle

| Run mode | Create | Cleanup |
|---|---|---|
| pytest | `tmp_path_factory.mktemp("e2e")` | pytest's tmp_path auto-cleanup |
| script (default) | `tempfile.mkdtemp(prefix="mkg-e2e-")` | script `finally`: `shutil.rmtree` |
| script `--keep-artifacts` | same | none; path printed to user |
| script `--work-dir <path>` | user-supplied | none; user-managed |

### Safety Checks (Runner Startup)

Runner validates in `__init__` or at the top of `run()`:

1. `config.work_dir` does not exist OR exists and is empty — otherwise `ValueError`.
2. `config.work_dir` is NOT the project root nor a child of `backend/` — prevents trashing the production SQLite. Allowed prefixes: system temp dir, `tests/` subtree.
3. `config.pdf_path.exists()` and `config.pdf_path.stat().st_size > 0`.

### External State Pollution

1. **LLM API quota**: unavoidable cost. Script prints a one-liner warning at startup: `"⚠ Running with live LLM. Est. cost ~$0.10, ~60s"`. No interactive confirmation.
2. **Neo4j DB**: default safe mode. Runner checks whether `Neo4jStore` exposes `clear_all`/equivalent; if not, skip with `unsafe_no_wipe`. `--neo4j-force` CLI flag allows opt-in pollution.
3. **`.env` / env vars**: read only, never written.

## Assertions

### Structural (13)

| # | Function | Assertion |
|---|---|---|
| 1 | `test_pdf_parsed` | `pdf_content is not None`; `len(full_text) > 500` |
| 2 | `test_pdf_has_title` | `pdf_content.title` non-empty |
| 3 | `test_extraction_returned` | `extracted is not None`; `extracted.concept_tree is not None` |
| 4 | `test_concept_tree_has_root` | `concept_tree.concept` non-empty |
| 5 | `test_concept_tree_has_children` | `len(concept_tree.children) >= 1` |
| 6 | `test_research_questions_nonempty` | `len(research_questions) >= 1` |
| 7 | `test_paper_stored` | `paper_doi == FIXTURE_EXPECTED_DOI`; `db.get_paper(paper_doi)` non-null |
| 8 | `test_graph_has_concepts` | `graph_stats["concepts"]["total"] > 0` |
| 9 | `test_graph_has_relations` | `graph_stats["relations"] > 0` |
| 10 | `test_graph_tree_renderable` | `len(graph_tree_text) > 0` |
| 11 | `test_obsidian_vault_exported` | `obsidian_vault_path.exists()`; `obsidian_file_count >= 1` |
| 12 | `test_obsidian_has_paper_note` | at least one `.md` in vault contains paper title or DOI |
| 13 | `test_neo4j_sync_or_skip` | if `neo4j_skipped_reason`: `pytest.skip(reason)` else `neo4j_stats["total_concepts"] > 0` |

### Loose Keyword Matching (3)

`FIXTURE_TOPIC_KEYWORDS` and `FIXTURE_EXPECTED_DOI` live in `fixture_metadata.py`. Initial values for `2305.11738v4` (CRITIC):

```python
FIXTURE_PDF_NAME = "e2e_sample.pdf"
FIXTURE_EXPECTED_DOI = "e2e_sample"   # derived from pdf_path.stem
FIXTURE_TOPIC_KEYWORDS = {
    "llm", "language model", "critic", "correct", "tool",
    "feedback", "reason", "reasoning", "evaluation",
    "大语言模型", "自我修正", "工具",
}
```

| # | Function | Assertion |
|---|---|---|
| 14 | `test_root_concept_topic_relevant` | `any(kw in root.lower() for kw in KEYWORDS)` |
| 15 | `test_any_child_topic_relevant` | any direct child hits keywords |
| 16 | `test_research_questions_topic_relevant` | joined research questions hit ≥ 2 keywords |

**Rule**: if a keyword assertion false-positives, grow the keyword set, do not loosen the count threshold.

## Script Output

On success, print a rich table:

```
┌─────────────────────┬──────────┬──────────────────┐
│ Stage               │ Time     │ Output           │
├─────────────────────┼──────────┼──────────────────┤
│ Parse PDF           │   0.42s  │ 12,483 chars     │
│ LLM extraction      │  38.71s  │ tree depth=3     │
│ Store paper         │   0.03s  │ doi=e2e_sample   │
│ Build graph         │   0.08s  │ 14 concepts      │
│ Export Obsidian     │   0.11s  │ 15 notes         │
│ Sync Neo4j          │   skip   │ not_connected    │
└─────────────────────┴──────────┴──────────────────┘
✓ E2E pipeline completed in 39.35s
```

On failure: red traceback + work directory path (even without `--keep-artifacts`) for post-mortem.

## Running It

### pytest Markers

`pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "e2e: end-to-end pipeline test with real LLM (slow, costs money)",
]
addopts = "-m 'not e2e'"
```

`tests/e2e/test_pipeline.py` top:

```python
pytestmark = pytest.mark.e2e
```

Invocation:

```bash
pytest -m e2e                    # only E2E
pytest -m "e2e or not e2e"       # everything
```

### conftest Fixture

```python
@pytest.fixture(scope="session")
def e2e_result(tmp_path_factory) -> E2EResult:
    work_dir = tmp_path_factory.mktemp("e2e")
    fixture_pdf = Path(__file__).parent.parent / "fixtures" / "e2e_sample.pdf"
    config = E2EConfig(pdf_path=fixture_pdf, work_dir=work_dir)
    return E2ERunner(config).run()
```

All 16 assertion functions take `e2e_result: E2EResult` as their single parameter.

### Script CLI

```
python scripts/e2e_test.py [OPTIONS]

Options:
  --pdf PATH           Custom PDF path (default: tests/fixtures/e2e_sample.pdf)
  --work-dir PATH      Custom work dir (default: tempfile.mkdtemp)
  --keep-artifacts     Do not clean work dir after run
  --no-obsidian        Skip Obsidian export stage
  --no-neo4j           Skip Neo4j sync stage
  --neo4j-force        Allow Neo4j sync even without safe-wipe (pollutes DB)
```

Exit codes: `0` success, `1` failure.

## Dependencies

No new dependencies. Uses existing `rich`, `typer`, `pytest`.

## Fixture Management

- `tests/fixtures/e2e_sample.pdf` is git-tracked (1.5 MB, below LFS threshold).
- Source: `papers/pending/2305.11738v4_1774912147.pdf` (CRITIC paper).
- To swap fixtures: replace the file AND update `fixture_metadata.py`. No other files need touching.

## Open Questions / Future Work

- If live LLM cost becomes a recurring pain, add a replay mode: run live once to capture, then replay from JSON fixture by default.
- If we want CI coverage later: `.github/workflows/e2e.yml` with `workflow_dispatch` + weekly schedule, requires `LLM_API_KEY` secret, Neo4j disabled.
- If `Neo4jStore` does not have a safe wipe method, consider adding one (`delete_all_concepts`) as a prerequisite for Stage 6 to actually run — out of scope for this spec.
