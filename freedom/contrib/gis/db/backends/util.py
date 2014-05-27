import warnings

from freedom.utils.deprecation import RemovedInFreedom19Warning

warnings.warn(
    "The freedom.contrib.gis.db.backends.util module has been renamed. "
    "Use freedom.contrib.gis.db.backends.utils instead.",
    RemovedInFreedom19Warning, stacklevel=2)

from freedom.contrib.gis.db.backends.utils import *  # NOQA
