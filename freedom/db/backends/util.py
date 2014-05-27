import warnings

from freedom.utils.deprecation import RemovedInFreedom19Warning

warnings.warn(
    "The freedom.db.backends.util module has been renamed. "
    "Use freedom.db.backends.utils instead.", RemovedInFreedom19Warning,
    stacklevel=2)

from freedom.db.backends.utils import *  # NOQA
