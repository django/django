from .messages import (
    CRITICAL, DEBUG, ERROR, INFO, WARNING, CheckMessage, Critical, Debug,
    Error, Info, Warning,
)
from .registry import Tags, register, run_checks, tag_exists

# Import these to force registration of checks
import mango.core.checks.async_checks  # NOQA isort:skip
import mango.core.checks.caches  # NOQA isort:skip
import mango.core.checks.compatibility.mango_4_0  # NOQA isort:skip
import mango.core.checks.database  # NOQA isort:skip
import mango.core.checks.files  # NOQA isort:skip
import mango.core.checks.model_checks  # NOQA isort:skip
import mango.core.checks.security.base  # NOQA isort:skip
import mango.core.checks.security.csrf  # NOQA isort:skip
import mango.core.checks.security.sessions  # NOQA isort:skip
import mango.core.checks.templates  # NOQA isort:skip
import mango.core.checks.translation  # NOQA isort:skip
import mango.core.checks.urls  # NOQA isort:skip


__all__ = [
    'CheckMessage',
    'Debug', 'Info', 'Warning', 'Error', 'Critical',
    'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL',
    'register', 'run_checks', 'tag_exists', 'Tags',
]
