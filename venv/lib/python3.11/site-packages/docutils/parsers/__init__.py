# $Id: __init__.py 9048 2022-03-29 21:50:15Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
This package contains Docutils parser modules.
"""

__docformat__ = 'reStructuredText'

from importlib import import_module

from docutils import Component, frontend


class Parser(Component):
    settings_spec = (
        'Generic Parser Options',
        None,
        (('Disable directives that insert the contents of an external file; '
          'replaced with a "warning" system message.',
          ['--no-file-insertion'],
          {'action': 'store_false', 'default': 1,
           'dest': 'file_insertion_enabled',
           'validator': frontend.validate_boolean}),
         ('Enable directives that insert the contents '
          'of an external file. (default)',
          ['--file-insertion-enabled'],
          {'action': 'store_true'}),
         ('Disable the "raw" directive; '
          'replaced with a "warning" system message.',
          ['--no-raw'],
          {'action': 'store_false', 'default': 1, 'dest': 'raw_enabled',
           'validator': frontend.validate_boolean}),
         ('Enable the "raw" directive. (default)',
          ['--raw-enabled'],
          {'action': 'store_true'}),
         ('Maximal number of characters in an input line. Default 10 000.',
          ['--line-length-limit'],
          {'metavar': '<length>', 'type': 'int', 'default': 10000,
           'validator': frontend.validate_nonnegative_int}),
         )
        )
    component_type = 'parser'
    config_section = 'parsers'

    def parse(self, inputstring, document):
        """Override to parse `inputstring` into document tree `document`."""
        raise NotImplementedError('subclass must override this method')

    def setup_parse(self, inputstring, document):
        """Initial parse setup.  Call at start of `self.parse()`."""
        self.inputstring = inputstring
        # provide fallbacks in case the document has only generic settings
        document.settings.setdefault('file_insertion_enabled', False)
        document.settings.setdefault('raw_enabled', False)
        document.settings.setdefault('line_length_limit', 10000)
        self.document = document
        document.reporter.attach_observer(document.note_parse_message)

    def finish_parse(self):
        """Finalize parse details.  Call at end of `self.parse()`."""
        self.document.reporter.detach_observer(
            self.document.note_parse_message)


_parser_aliases = {  # short names for known parsers
                   'null': 'docutils.parsers.null',
                   # reStructuredText
                   'rst': 'docutils.parsers.rst',
                   'restructuredtext': 'docutils.parsers.rst',
                   'rest': 'docutils.parsers.rst',
                   'restx': 'docutils.parsers.rst',
                   'rtxt': 'docutils.parsers.rst',
                   # 3rd-party Markdown parsers
                   'recommonmark': 'docutils.parsers.recommonmark_wrapper',
                   'myst': 'myst_parser.docutils_',
                   # 'pycmark': works out of the box
                   # dispatcher for 3rd-party Markdown parsers
                   'commonmark': 'docutils.parsers.commonmark_wrapper',
                   'markdown': 'docutils.parsers.commonmark_wrapper',
                  }


def get_parser_class(parser_name):
    """Return the Parser class from the `parser_name` module."""
    name = parser_name.lower()
    try:
        module = import_module(_parser_aliases.get(name, name))
    except ImportError as err:
        raise ImportError(f'Parser "{parser_name}" not found. {err}')
    return module.Parser
