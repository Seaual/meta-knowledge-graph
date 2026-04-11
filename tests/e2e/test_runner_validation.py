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
    repo_root = Path(__file__).resolve().parents[2]
    with pytest.raises(ValueError, match="project root"):
        _validate_work_dir(repo_root)


def test_rejects_backend_subtree(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    backend_child = repo_root / "backend" / "oops"
    with pytest.raises(ValueError, match="backend"):
        _validate_work_dir(backend_child)
