"""DeepAgents memory and persistence configuration."""

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.sqlite import SqliteStore


def build_checkpointer(db_path: str) -> SqliteSaver:
    """Build SQLite-backed checkpointer for thread state."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return SqliteSaver(conn=conn)


def build_store(db_path: str) -> SqliteStore:
    """Build SQLite-backed store for cross-thread memory."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return SqliteStore(conn=conn)
