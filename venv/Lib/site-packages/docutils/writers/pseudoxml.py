# $Id: pseudoxml.py 10136 2025-05-20 15:48:27Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
Simple internal document tree Writer, writes indented pseudo-XML.
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

from docutils import writers, frontend


class Writer(writers.Writer):

    supported = ('pseudoxml', 'pprint', 'pformat')
    """Formats this writer supports."""

    settings_spec = (
        '"Docutils pseudo-XML" Writer Options',
        None,
        (('Pretty-print <#text> nodes.',
          ['--detailed'],
          {'action': 'store_true', 'validator': frontend.validate_boolean}),
         )
        )

    config_section = 'pseudoxml writer'
    config_section_dependencies = ('writers',)

    output = None
    """Final translated form of `document`."""

    def translate(self) -> None:
        self.output = self.document.pformat()

    def supports(self, format) -> bool:
        """This writer supports all format-specific elements."""
        return True
