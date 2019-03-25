# -*- coding: utf-8 -*-
"""
    sphinx.util.build_phase
    ~~~~~~~~~~~~~~~~~~~~~~~

    Build phase of Sphinx application.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

try:
    from enum import IntEnum
except ImportError:  # py27
    IntEnum = object  # type: ignore


class BuildPhase(IntEnum):
    """Build phase of Sphinx application."""
    INITIALIZATION = 1
    READING = 2
    CONSISTENCY_CHECK = 3
    RESOLVING = 3
    WRITING = 4
