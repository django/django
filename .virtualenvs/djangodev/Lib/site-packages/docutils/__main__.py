#!/usr/bin/env python3
# :Copyright: © 2020, 2022 Günter Milde.
# :License: Released under the terms of the `2-Clause BSD license`_, in short:
#
#    Copying and distribution of this file, with or without modification,
#    are permitted in any medium without royalty provided the copyright
#    notice and this notice are preserved.
#    This file is offered as-is, without any warranty.
#
# .. _2-Clause BSD license: https://opensource.org/licenses/BSD-2-Clause
#
# Revision: $Revision: 9107 $
# Date: $Date: 2022-07-06 15:59:57 +0200 (Mi, 06. Jul 2022) $

"""Generic command line interface for the `docutils` package.

See also
https://docs.python.org/3/library/__main__.html#main-py-in-python-packages
"""

import argparse
import locale
import sys

import docutils
from docutils.core import Publisher, publish_cmdline, default_description


class CliSettingsSpec(docutils.SettingsSpec):
    """Runtime settings & command-line options for the generic CLI.

    Configurable reader, parser, and writer components.

    The "--writer" default will change to 'html' in Docutils 2.0
    when 'html' becomes an alias for the current value 'html5'.
    """

    settings_spec = (
        'Docutils Application Options',
        'Reader, writer, and parser settings influence the available options. '
        '  Example: use `--help --writer=latex` to see LaTeX writer options. ',
        # options: ('help text', [<option strings>], {<keyword arguments>})
        (('Reader name (currently: "%default").',
          ['--reader'], {'default': 'standalone', 'metavar': '<reader>'}),
         ('Parser name (currently: "%default").',
          ['--parser'], {'default': 'rst', 'metavar': '<parser>'}),
         ('Writer name (currently: "%default").',
          ['--writer'], {'default': 'html5', 'metavar': '<writer>'}),
         )
    )
    config_section = 'docutils application'
    config_section_dependencies = ('docutils-cli application',  # back-compat
                                   'applications')


def main():
    """Generic command line interface for the Docutils Publisher.
    """
    locale.setlocale(locale.LC_ALL, '')

    description = ('Convert documents into useful formats.  '
                   + default_description)

    # Update component selection from config file(s)
    components = Publisher().get_settings(settings_spec=CliSettingsSpec)

    # Update component selection from command-line
    argparser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    argparser.add_argument('--reader', default=components.reader)
    argparser.add_argument('--parser', default=components.parser)
    argparser.add_argument('--writer', default=components.writer)
    # other options are parsed in a second pass via `publish_cmdline()`
    (args, remainder) = argparser.parse_known_args()
    # Ensure the current component selections are shown in help:
    CliSettingsSpec.settings_default_overrides = args.__dict__

    try:
        publish_cmdline(reader_name=args.reader,
                        parser_name=args.parser,
                        writer_name=args.writer,
                        settings_spec=CliSettingsSpec,
                        description=description,
                        argv=remainder)
    except ImportError as error:
        print('%s.' % error, file=sys.stderr)
        if '--traceback' in remainder:
            raise
        else:
            print('Use "--traceback" to show details.')


if __name__ == '__main__':
    if sys.argv[0].endswith('__main__.py'):
        # fix "usage" message
        sys.argv[0] = '%s -m docutils' % sys.executable
    main()
