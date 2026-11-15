"""SQLite persistence package (schema.sql + typed store)."""

from .store import (DEGRADATION_LEVELS, DEFAULT_LOT_MULTIPLIERS, NewSetupDB)

__all__ = ["DEGRADATION_LEVELS", "DEFAULT_LOT_MULTIPLIERS", "NewSetupDB"]
