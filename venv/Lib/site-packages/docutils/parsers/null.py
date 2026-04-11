# $Id: null.py 10136 2025-05-20 15:48:27Z milde $
# Author: Martin Blais <blais@furius.ca>
# Copyright: This module has been placed in the public domain.

"""A do-nothing parser."""

from __future__ import annotations

__docformat__ = 'reStructuredText'

from docutils import parsers


class Parser(parsers.Parser):

    """A do-nothing parser."""

    supported = ('null',)

    config_section = 'null parser'
    config_section_dependencies = ('parsers',)

    def parse(self, inputstring, document) -> None:
        pass
