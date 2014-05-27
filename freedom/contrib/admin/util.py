import warnings

from freedom.utils.deprecation import RemovedInFreedom19Warning

warnings.warn(
    "The freedom.contrib.admin.util module has been renamed. "
    "Use freedom.contrib.admin.utils instead.", RemovedInFreedom19Warning)

from freedom.contrib.admin.utils import *  # NOQA
