"""DeepAgents memory and persistence configuration."""

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore


def build_checkpointer(db_path: str) -> SqliteSaver:
    """Build SQLite-backed checkpointer for thread state."""
    return SqliteSaver.from_conn_string(db_path)


def build_store(db_path: str) -> SqliteStore:
    """Build SQLite-backed store for cross-thread memory."""
    return SqliteStore(db_path=db_path)
