# -*- coding: utf-8 -*-
"""
    sphinx.util.typing
    ~~~~~~~~~~~~~~~~~~

    The composit types for Sphinx.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from typing import Callable, Dict, List, Tuple

from docutils import nodes
from docutils.parsers.rst.states import Inliner
from six import PY3


if PY3:
    unicode = str

# common role functions
RoleFunction = Callable[[unicode, unicode, unicode, int, Inliner, Dict, List[unicode]],
                        Tuple[List[nodes.Node], List[nodes.Node]]]

# title getter functions for enumerable nodes (see sphinx.domains.std)
TitleGetter = Callable[[nodes.Node], unicode]
