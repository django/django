# $Id: __init__.py 10045 2025-03-09 01:02:23Z aa-turner $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
This package contains Docutils parser modules.
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

import importlib

from docutils import Component, frontend, transforms

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Final

    from docutils import nodes
    from docutils.transforms import Transform


class Parser(Component):
    settings_spec = (
        'Generic Parser Options',
        None,
        (('Disable directives that insert the contents of an external file; '
          'replaced with a "warning" system message.',
          ['--no-file-insertion'],
          {'action': 'store_false', 'default': True,
           'dest': 'file_insertion_enabled',
           'validator': frontend.validate_boolean}),
         ('Enable directives that insert the contents '
          'of an external file. (default)',
          ['--file-insertion-enabled'],
          {'action': 'store_true'}),
         ('Disable the "raw" directive; '
          'replaced with a "warning" system message.',
          ['--no-raw'],
          {'action': 'store_false', 'default': True, 'dest': 'raw_enabled',
           'validator': frontend.validate_boolean}),
         ('Enable the "raw" directive. (default)',
          ['--raw-enabled'],
          {'action': 'store_true'}),
         ('Maximal number of characters in an input line. Default 10 000.',
          ['--line-length-limit'],
          {'metavar': '<length>', 'type': 'int', 'default': 10_000,
           'validator': frontend.validate_nonnegative_int}),
         ('Validate the document tree after parsing.',
          ['--validate'],
          {'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Do not validate the document tree. (default)',
          ['--no-validation'],
          {'action': 'store_false', 'dest': 'validate'}),
         )
        )
    component_type: Final = 'parser'
    config_section: Final = 'parsers'

    def get_transforms(self) -> list[type[Transform]]:
        return super().get_transforms() + [transforms.universal.Validate]

    def parse(self, inputstring: str, document: nodes.document) -> None:
        """Override to parse `inputstring` into document tree `document`."""
        raise NotImplementedError('subclass must override this method')

    def setup_parse(self, inputstring: str, document: nodes.document) -> None:
        """Initial parse setup.  Call at start of `self.parse()`."""
        self.inputstring = inputstring
        # provide fallbacks in case the document has only generic settings
        document.settings.setdefault('file_insertion_enabled', False)
        document.settings.setdefault('raw_enabled', False)
        document.settings.setdefault('line_length_limit', 10_000)
        self.document = document
        document.reporter.attach_observer(document.note_parse_message)

    def finish_parse(self) -> None:
        """Finalize parse details.  Call at end of `self.parse()`."""
        self.document.reporter.detach_observer(
            self.document.note_parse_message)


PARSER_ALIASES = {  # short names for known parsers
                  'null': 'docutils.parsers.null',
                  # reStructuredText
                  'rst': 'docutils.parsers.rst',
                  'restructuredtext': 'docutils.parsers.rst',
                  'rest': 'docutils.parsers.rst',
                  'restx': 'docutils.parsers.rst',
                  'rtxt': 'docutils.parsers.rst',
                  # Docutils XML
                  'docutils_xml': 'docutils.parsers.docutils_xml',
                  'xml': 'docutils.parsers.docutils_xml',
                  # 3rd-party Markdown parsers
                  'recommonmark': 'docutils.parsers.recommonmark_wrapper',
                  'myst': 'myst_parser.docutils_',
                  # 'pycmark': works out of the box
                  # dispatcher for 3rd-party Markdown parsers
                  'commonmark': 'docutils.parsers.commonmark_wrapper',
                  'markdown': 'docutils.parsers.commonmark_wrapper',
                  }


def get_parser_class(parser_name: str) -> type[Parser]:
    """Return the Parser class from the `parser_name` module."""
    name = parser_name.lower()

    try:
        module = importlib.import_module(PARSER_ALIASES.get(name, name))
    except ImportError as err:
        raise ImportError(f'Parser "{parser_name}" not found. {err}') from err
    return module.Parser
