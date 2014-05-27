import warnings

from freedom.utils.deprecation import RemovedInFreedom19Warning

warnings.warn(
    "The freedom.forms.util module has been renamed. "
    "Use freedom.forms.utils instead.", RemovedInFreedom19Warning, stacklevel=2)

from freedom.forms.utils import *  # NOQA
