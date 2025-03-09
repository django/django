"""
Constants used across the ORM in general.
"""

from enum import Enum

# Separator used to split filter strings apart.
LOOKUP_SEP = "__"


class OnConflict(Enum):
    IGNORE = "ignore"
    UPDATE = "update"
