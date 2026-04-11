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
