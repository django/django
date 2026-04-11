# $Id: pep.py 10136 2025-05-20 15:48:27Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
Python Enhancement Proposal (PEP) Reader.
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

from docutils.readers import standalone
from docutils.transforms import peps, frontmatter
from docutils.parsers import rst


class Reader(standalone.Reader):

    supported = ('pep',)
    """Contexts this reader supports."""

    settings_spec = (
        'PEP Reader Option Defaults',
        'The --pep-references and --rfc-references options (for the '
        'reStructuredText parser) are on by default.',
        ())

    config_section = 'pep reader'
    config_section_dependencies = ('readers', 'standalone reader')

    def get_transforms(self):
        transforms = super().get_transforms()
        # We have PEP-specific frontmatter handling.
        transforms.remove(frontmatter.DocTitle)
        transforms.remove(frontmatter.SectionSubTitle)
        transforms.remove(frontmatter.DocInfo)
        transforms.extend([peps.Headers, peps.Contents, peps.TargetNotes])
        return transforms

    settings_default_overrides = {'pep_references': True,
                                  'rfc_references': True}

    inliner_class = rst.states.Inliner

    def __init__(self, parser=None, parser_name=None) -> None:
        """`parser` should be ``None``, `parser_name` is ignored.

        The default parser is "rst" with PEP-specific settings
        (since Docutils 0.3). Since Docutils 0.22, `parser` is ignored,
        if it is a `str` instance.
        """
        if parser is None or isinstance(parser, str):
            parser = rst.Parser(rfc2822=True, inliner=self.inliner_class())
        super().__init__(parser)
