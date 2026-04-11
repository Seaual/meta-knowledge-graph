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
