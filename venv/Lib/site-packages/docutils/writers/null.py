# $Id: null.py 10136 2025-05-20 15:48:27Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
A do-nothing Writer.

`self.output` changed from ``None`` to the empty string
in Docutils 0.22.
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

from docutils import writers


class Writer(writers.UnfilteredWriter):

    supported = ('null',)
    """Formats this writer supports."""

    config_section = 'null writer'
    config_section_dependencies = ('writers',)

    def translate(self) -> None:
        self.output = ''
