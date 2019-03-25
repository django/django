#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

"""Module that contains the command line app.

Why does this file exist, and why not put this in __main__?
  You might be tempted to import things from __main__ later, but that will
  cause problems: the code will get executed twice:
  - When you run `python -m sqlparse` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``sqlparse.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``sqlparse.__main__`` in ``sys.modules``.
  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""

import argparse
import sys
from io import TextIOWrapper
from codecs import open, getreader

import sqlparse
from sqlparse.compat import PY2
from sqlparse.exceptions import SQLParseError


# TODO: Add CLI Tests
# TODO: Simplify formatter by using argparse `type` arguments
def create_parser():
    _CASE_CHOICES = ['upper', 'lower', 'capitalize']

    parser = argparse.ArgumentParser(
        prog='sqlformat',
        description='Format FILE according to OPTIONS. Use "-" as FILE '
                    'to read from stdin.',
        usage='%(prog)s  [OPTIONS] FILE, ...',
    )

    parser.add_argument('filename')

    parser.add_argument(
        '-o', '--outfile',
        dest='outfile',
        metavar='FILE',
        help='write output to FILE (defaults to stdout)')

    parser.add_argument(
        '--version',
        action='version',
        version=sqlparse.__version__)

    group = parser.add_argument_group('Formatting Options')

    group.add_argument(
        '-k', '--keywords',
        metavar='CHOICE',
        dest='keyword_case',
        choices=_CASE_CHOICES,
        help='change case of keywords, CHOICE is one of {0}'.format(
            ', '.join('"{0}"'.format(x) for x in _CASE_CHOICES)))

    group.add_argument(
        '-i', '--identifiers',
        metavar='CHOICE',
        dest='identifier_case',
        choices=_CASE_CHOICES,
        help='change case of identifiers, CHOICE is one of {0}'.format(
            ', '.join('"{0}"'.format(x) for x in _CASE_CHOICES)))

    group.add_argument(
        '-l', '--language',
        metavar='LANG',
        dest='output_format',
        choices=['python', 'php'],
        help='output a snippet in programming language LANG, '
             'choices are "python", "php"')

    group.add_argument(
        '--strip-comments',
        dest='strip_comments',
        action='store_true',
        default=False,
        help='remove comments')

    group.add_argument(
        '-r', '--reindent',
        dest='reindent',
        action='store_true',
        default=False,
        help='reindent statements')

    group.add_argument(
        '--indent_width',
        dest='indent_width',
        default=2,
        type=int,
        help='indentation width (defaults to 2 spaces)')

    group.add_argument(
        '-a', '--reindent_aligned',
        action='store_true',
        default=False,
        help='reindent statements to aligned format')

    group.add_argument(
        '-s', '--use_space_around_operators',
        action='store_true',
        default=False,
        help='place spaces around mathematical operators')

    group.add_argument(
        '--wrap_after',
        dest='wrap_after',
        default=0,
        type=int,
        help='Column after which lists should be wrapped')

    group.add_argument(
        '--comma_first',
        dest='comma_first',
        default=False,
        type=bool,
        help='Insert linebreak before comma (default False)')

    group.add_argument(
        '--encoding',
        dest='encoding',
        default='utf-8',
        help='Specify the input encoding (default utf-8)')

    return parser


def _error(msg):
    """Print msg and optionally exit with return code exit_."""
    sys.stderr.write(u'[ERROR] {0}\n'.format(msg))
    return 1


def main(args=None):
    parser = create_parser()
    args = parser.parse_args(args)

    if args.filename == '-':  # read from stdin
        if PY2:
            data = getreader(args.encoding)(sys.stdin).read()
        else:
            data = TextIOWrapper(
                sys.stdin.buffer, encoding=args.encoding).read()
    else:
        try:
            with open(args.filename, 'r', args.encoding) as f:
                data = ''.join(f.readlines())
        except IOError as e:
            return _error(
                u'Failed to read {0}: {1}'.format(args.filename, e))

    close_stream = False
    if args.outfile:
        try:
            stream = open(args.outfile, 'w', args.encoding)
            close_stream = True
        except IOError as e:
            return _error(u'Failed to open {0}: {1}'.format(args.outfile, e))
    else:
        stream = sys.stdout

    formatter_opts = vars(args)
    try:
        formatter_opts = sqlparse.formatter.validate_options(formatter_opts)
    except SQLParseError as e:
        return _error(u'Invalid options: {0}'.format(e))

    s = sqlparse.format(data, **formatter_opts)
    stream.write(s)
    stream.flush()
    if close_stream:
        stream.close()
    return 0
