"""Session-scoped fixture that runs the E2E pipeline exactly once per session.

All `test_*` functions in `tests/e2e/test_pipeline.py` share this single
result to keep LLM costs to one call per `pytest -m e2e` invocation.
"""

import sys

# Ensure UTF-8 output on Windows (GBK console corrupts CJK text in test output)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

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
    config = E2EConfig(
        pdf_path=FIXTURE_PDF_PATH,
        work_dir=work_dir,
        enable_neo4j=True,  # will likely skip with unsafe_no_wipe / not_connected
        enable_obsidian=True,
        llm_config_source_db=_PROJECT_DB if _PROJECT_DB.exists() else None,
    )
    return E2ERunner(config).run()
