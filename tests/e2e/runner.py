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
