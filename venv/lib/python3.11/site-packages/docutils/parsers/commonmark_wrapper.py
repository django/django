#! /usr/bin/env python3
# :Copyright: © 2022 Günter Milde.
# :License: Released under the terms of the `2-Clause BSD license`_, in short:
#
#    Copying and distribution of this file, with or without modification,
#    are permitted in any medium without royalty provided the copyright
#    notice and this notice are preserved.
#    This file is offered as-is, without any warranty.
#
# .. _2-Clause BSD license: https://opensource.org/licenses/BSD-2-Clause
#
# Revision: $Revision: 9048 $
# Date: $Date: 2022-03-29 23:50:15 +0200 (Di, 29. Mär 2022) $
"""
An interface for parsing CommonMark input.

Select a locally installed parser from the following 3rd-party
parser packages:

:pycmark:       https://pypi.org/project/pycmark/
:myst:          https://pypi.org/project/pycmark/
:recommonmark:  https://pypi.org/project/pycmark/ (unmaintained, deprecated)

The first parser class that can be successfully imported is mapped to
`commonmark_wrapper.Parser`.

This module is provisional:
the API is not settled and may change with any minor Docutils version.
"""

import docutils.parsers


commonmark_parser_names = ('pycmark', 'myst', 'recommonmark')
"""Names of compatible drop-in CommonMark parsers"""

Parser = None
parser_name = ''

for name in commonmark_parser_names:
    try:
        Parser = docutils.parsers.get_parser_class(name)
    except ImportError:
        continue
    parser_name = name
    break

if Parser is None:
    raise ImportError(
              'Parsing "CommonMark" requires one of the packages\n'
              f'{commonmark_parser_names} available at https://pypi.org')

if parser_name == 'myst':
    if not Parser.settings_defaults:
        Parser.settings_defaults = {}
    Parser.settings_defaults['myst_commonmark_only'] = True
