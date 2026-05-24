"""DeepAgents filesystem backend configuration."""

from pathlib import Path

from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend


def build_filesystem_backend(workspace_dir: str) -> CompositeBackend:
    """Build CompositeBackend with per-thread workspace."""
    root = Path(workspace_dir)
    root.mkdir(parents=True, exist_ok=True)

    return CompositeBackend(
        default=StateBackend(),
        routes={
            "/workspace/": FilesystemBackend(
                root_dir=str(root),
                virtual_mode=True,
            ),
        },
    )
