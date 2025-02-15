from .messages import (
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    WARNING,
    CheckMessage,
    Critical,
    Debug,
    Error,
    Info,
    Warning,
)
from .registry import Tags, register, run_checks, tag_exists

# Import these to force registration of checks
import thibaud.core.checks.async_checks  # NOQA isort:skip
import thibaud.core.checks.caches  # NOQA isort:skip
import thibaud.core.checks.commands  # NOQA isort:skip
import thibaud.core.checks.compatibility.thibaud_4_0  # NOQA isort:skip
import thibaud.core.checks.database  # NOQA isort:skip
import thibaud.core.checks.files  # NOQA isort:skip
import thibaud.core.checks.model_checks  # NOQA isort:skip
import thibaud.core.checks.security.base  # NOQA isort:skip
import thibaud.core.checks.security.csrf  # NOQA isort:skip
import thibaud.core.checks.security.sessions  # NOQA isort:skip
import thibaud.core.checks.templates  # NOQA isort:skip
import thibaud.core.checks.translation  # NOQA isort:skip
import thibaud.core.checks.urls  # NOQA isort:skip


__all__ = [
    "CheckMessage",
    "Debug",
    "Info",
    "Warning",
    "Error",
    "Critical",
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
    "register",
    "run_checks",
    "tag_exists",
    "Tags",
]
