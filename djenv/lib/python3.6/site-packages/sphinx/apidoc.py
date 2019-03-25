# -*- coding: utf-8 -*-
"""
    sphinx.apidoc
    ~~~~~~~~~~~~~

    This file has moved to :py:mod:`sphinx.ext.apidoc`.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys
import warnings

from sphinx.deprecation import RemovedInSphinx20Warning
from sphinx.ext.apidoc import main as _main

if False:
    # For type annotation
    from typing import List  # NOQA
    from sphinx.application import Sphinx  # NOQA


def main(argv=sys.argv):
    # type: (List[str]) -> None
    warnings.warn(
        '`sphinx.apidoc.main()` has moved to `sphinx.ext.apidoc.main()`.',
        RemovedInSphinx20Warning,
        stacklevel=2,
    )
    _main(argv[1:])  # skip first argument to adjust arguments (refs: #4615)


# So program can be started with "python -m sphinx.apidoc ..."
if __name__ == "__main__":
    warnings.warn(
        '`sphinx.apidoc` has moved to `sphinx.ext.apidoc`.',
        RemovedInSphinx20Warning,
        stacklevel=2,
    )
    main()
