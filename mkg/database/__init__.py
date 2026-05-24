# mkg/database/__init__.py
"""Database package - exports Database class"""

from .core import DatabaseCore
from .schema import SchemaMixin
from .migrations import MigrationMixin
from .compat import CompatMixin

class Database(DatabaseCore, SchemaMixin, MigrationMixin, CompatMixin):
    """SQLite database manager - composed from mixins"""
    pass
