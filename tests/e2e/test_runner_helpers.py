"""Tests for runner helpers (no live LLM required)."""

import time

from rich.tree import Tree

from tests.e2e.runner import _has_safe_wipe, _render_tree_text, _timed


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


def test_neo4j_has_clear_all():
    """Neo4jStore.clear_all must exist for safe E2E test isolation."""
    from mkg.neo4j_store import Neo4jStore

    assert hasattr(Neo4jStore, "clear_all")
    assert callable(getattr(Neo4jStore, "clear_all"))
    assert _has_safe_wipe(Neo4jStore())
