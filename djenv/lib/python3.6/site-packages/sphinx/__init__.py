# -*- coding: utf-8 -*-
"""
    Sphinx
    ~~~~~~

    The Sphinx documentation toolchain.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# Keep this file executable as-is in Python 3!
# (Otherwise getting the version out of it from setup.py is impossible.)

from __future__ import absolute_import

import os
import sys
import warnings
from os import path

from .deprecation import RemovedInNextVersionWarning
from .deprecation import RemovedInSphinx20Warning

if False:
    # For type annotation
    # note: Don't use typing.TYPE_CHECK here (for py27 and py34).
    from typing import Any, List  # NOQA


# by default, all DeprecationWarning under sphinx package will be emit.
# Users can avoid this by using environment variable: PYTHONWARNINGS=
if 'PYTHONWARNINGS' not in os.environ:
    warnings.filterwarnings('default', category=RemovedInNextVersionWarning)
# docutils.io using mode='rU' for open
warnings.filterwarnings('ignore', "'U' mode is deprecated",
                        DeprecationWarning, module='docutils.io')

__version__ = '1.8.5'
__released__ = '1.8.5'  # used when Sphinx builds its own docs

#: Version info for better programmatic use.
#:
#: A tuple of five elements; for Sphinx version 1.2.1 beta 3 this would be
#: ``(1, 2, 1, 'beta', 3)``. The fourth element can be one of: ``alpha``,
#: ``beta``, ``rc``, ``final``. ``final`` always has 0 as the last element.
#:
#: .. versionadded:: 1.2
#:    Before version 1.2, check the string ``sphinx.__version__``.
version_info = (1, 8, 5, 'final', 0)

package_dir = path.abspath(path.dirname(__file__))

__display_version__ = __version__  # used for command line version
if __version__.endswith('+'):
    # try to find out the commit hash if checked out from git, and append
    # it to __version__ (since we use this value from setup.py, it gets
    # automatically propagated to an installed copy as well)
    __display_version__ = __version__
    __version__ = __version__[:-1]  # remove '+' for PEP-440 version spec.
    try:
        import subprocess
        p = subprocess.Popen(['git', 'show', '-s', '--pretty=format:%h'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if out:
            __display_version__ += '/' + out.decode().strip()
    except Exception:
        pass


def main(argv=sys.argv):  # type: ignore
    # type: (List[unicode]) -> int
    from .cmd import build
    warnings.warn(
        '`sphinx.main()` has moved to `sphinx.cmd.build.main()`.',
        RemovedInSphinx20Warning,
        stacklevel=2,
    )
    argv = argv[1:]  # skip first argument to adjust arguments (refs: #4615)
    return build.main(argv)


def build_main(argv=sys.argv):
    """Sphinx build "main" command-line entry."""
    from .cmd import build
    warnings.warn(
        '`sphinx.build_main()` has moved to `sphinx.cmd.build.build_main()`.',
        RemovedInSphinx20Warning,
        stacklevel=2,
    )
    return build.build_main(argv[1:])  # skip first argument to adjust arguments (refs: #4615)


def make_main(argv=sys.argv):
    """Sphinx build "make mode" entry."""
    from .cmd import build
    warnings.warn(
        '`sphinx.build_main()` has moved to `sphinx.cmd.build.make_main()`.',
        RemovedInSphinx20Warning,
        stacklevel=2,
    )
    return build.make_main(argv[1:])  # skip first argument to adjust arguments (refs: #4615)


if __name__ == '__main__':
    from .cmd import build
    warnings.warn(
        '`sphinx` has moved to `sphinx.build`.',
        RemovedInSphinx20Warning,
        stacklevel=2,
    )
    build.main()
