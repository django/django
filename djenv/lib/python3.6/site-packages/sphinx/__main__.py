# -*- coding: utf-8 -*-
"""
    sphinx.__main__
    ~~~~~~~~~~~~~~~

    The Sphinx documentation toolchain.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys

from sphinx.cmd.build import main

sys.exit(main(sys.argv[1:]))  # type: ignore
