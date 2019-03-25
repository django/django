# -*- coding: utf-8 -*-
"""
    sphinx.make_mode
    ~~~~~~~~~~~~~~~~

    sphinx-build -M command-line handling.

    This replaces the old, platform-dependent and once-generated content
    of Makefile / make.bat.

    This is in its own module so that importing it is fast.  It should not
    import the main Sphinx modules (like sphinx.applications, sphinx.builders).

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import warnings

from sphinx.cmd import make_mode
from sphinx.deprecation import RemovedInSphinx30Warning


BUILDERS = make_mode.BUILDERS


class Make(make_mode.Make):
    def __init__(self, *args):
        warnings.warn('sphinx.make_mode.Make is deprecated. '
                      'Please use sphinx.cmd.make_mode.Make instead.',
                      RemovedInSphinx30Warning, stacklevel=2)
        super(Make, self).__init__(*args)


def run_make_mode(args):
    warnings.warn('sphinx.make_mode.run_make_mode() is deprecated. '
                  'Please use sphinx.cmd.make_mode.run_make_mode() instead.',
                  RemovedInSphinx30Warning, stacklevel=2)
    return make_mode.run_make_mode(args)
