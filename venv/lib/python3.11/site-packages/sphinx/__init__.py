"""The Sphinx documentation toolchain."""

# Keep this file executable as-is in Python 3!
# (Otherwise getting the version out of it when packaging is impossible.)

import os
import warnings
from os import path

from .deprecation import RemovedInNextVersionWarning

# by default, all DeprecationWarning under sphinx package will be emit.
# Users can avoid this by using environment variable: PYTHONWARNINGS=
if 'PYTHONWARNINGS' not in os.environ:
    warnings.filterwarnings('default', category=RemovedInNextVersionWarning)
# docutils.io using mode='rU' for open
warnings.filterwarnings('ignore', "'U' mode is deprecated",
                        DeprecationWarning, module='docutils.io')
warnings.filterwarnings('ignore', 'The frontend.Option class .*',
                        DeprecationWarning, module='docutils.frontend')

__version__ = '7.2.6'
__display_version__ = __version__  # used for command line version

#: Version info for better programmatic use.
#:
#: A tuple of five elements; for Sphinx version 1.2.1 beta 3 this would be
#: ``(1, 2, 1, 'beta', 3)``. The fourth element can be one of: ``alpha``,
#: ``beta``, ``rc``, ``final``. ``final`` always has 0 as the last element.
#:
#: .. versionadded:: 1.2
#:    Before version 1.2, check the string ``sphinx.__version__``.
version_info = (7, 2, 6, 'final', 0)

package_dir = path.abspath(path.dirname(__file__))

_in_development = False
if _in_development:
    # Only import subprocess if needed
    import subprocess

    try:
        if ret := subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=package_dir,
            capture_output=True,
            encoding='ascii',
            errors='surrogateescape',
        ).stdout:
            __display_version__ += '+/' + ret.strip()
        del ret
    finally:
        del subprocess
del _in_development
