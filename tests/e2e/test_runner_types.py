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
    assert cfg.llm_config_source_db is None


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
