# -*- coding: utf-8 -*-
"""
    sphinx.cmdline
    ~~~~~~~~~~~~~~

    sphinx-build command-line handling.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import absolute_import
from __future__ import print_function

import sys
import warnings

from sphinx.cmd import build
from sphinx.deprecation import RemovedInSphinx30Warning

if False:
    # For type annotation
    import argparse  # NOQA
    from typing import Any, IO, List, Union  # NOQA
    from sphinx.application import Sphinx  # NOQA


def handle_exception(app, args, exception, stderr=sys.stderr):
    # type: (Sphinx, Any, Union[Exception, KeyboardInterrupt], IO) -> None
    warnings.warn('sphinx.cmdline module is deprecated. Use sphinx.cmd.build instead.',
                  RemovedInSphinx30Warning, stacklevel=2)
    build.handle_exception(app, args, exception, stderr)


def jobs_argument(value):
    # type: (str) -> int
    warnings.warn('sphinx.cmdline module is deprecated. Use sphinx.cmd.build instead.',
                  RemovedInSphinx30Warning, stacklevel=2)
    return build.jobs_argument(value)


def get_parser():
    # type: () -> argparse.ArgumentParser
    warnings.warn('sphinx.cmdline module is deprecated. Use sphinx.cmd.build instead.',
                  RemovedInSphinx30Warning, stacklevel=2)
    return build.get_parser()


def main(argv=sys.argv[1:]):  # type: ignore
    # type: (List[unicode]) -> int
    warnings.warn('sphinx.cmdline module is deprecated. Use sphinx.cmd.build instead.',
                  RemovedInSphinx30Warning, stacklevel=2)
    return build.main(argv)
