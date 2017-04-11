import warnings

warnings.warn(
    "channels.tests package is deprecated. Use channels.test",
    DeprecationWarning,
)

from channels.test import *  # NOQA isort:skip
