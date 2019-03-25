# -*- coding: utf-8 -*-
"""
    sphinx.util.console
    ~~~~~~~~~~~~~~~~~~~

    Format colored console output.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import os
import re
import sys

try:
    # check if colorama is installed to support color on Windows
    import colorama
except ImportError:
    colorama = None

if False:
    # For type annotation
    from typing import Dict  # NOQA


_ansi_re = re.compile('\x1b\\[(\\d\\d;){0,2}\\d\\dm')
codes = {}  # type: Dict[str, str]


def get_terminal_width():
    # type: () -> int
    """Borrowed from the py lib."""
    try:
        import termios
        import fcntl
        import struct
        call = fcntl.ioctl(0, termios.TIOCGWINSZ,
                           struct.pack('hhhh', 0, 0, 0, 0))
        height, width = struct.unpack('hhhh', call)[:2]
        terminal_width = width
    except Exception:
        # FALLBACK
        terminal_width = int(os.environ.get('COLUMNS', "80")) - 1
    return terminal_width


_tw = get_terminal_width()


def term_width_line(text):
    # type: (str) -> str
    if not codes:
        # if no coloring, don't output fancy backspaces
        return text + '\n'
    else:
        # codes are not displayed, this must be taken into account
        return text.ljust(_tw + len(text) - len(_ansi_re.sub('', text))) + '\r'


def color_terminal():
    # type: () -> bool
    if sys.platform == 'win32' and colorama is not None:
        colorama.init()
        return True
    if not hasattr(sys.stdout, 'isatty'):
        return False
    if not sys.stdout.isatty():
        return False
    if 'COLORTERM' in os.environ:
        return True
    term = os.environ.get('TERM', 'dumb').lower()
    if term in ('xterm', 'linux') or 'color' in term:
        return True
    return False


def nocolor():
    # type: () -> None
    if sys.platform == 'win32' and colorama is not None:
        colorama.deinit()
    codes.clear()


def coloron():
    # type: () -> None
    codes.update(_orig_codes)


def colorize(name, text, input_mode=False):
    # type: (str, unicode, bool) -> unicode
    def escseq(name):
        # Wrap escape sequence with ``\1`` and ``\2`` to let readline know
        # it is non-printable characters
        # ref: https://tiswww.case.edu/php/chet/readline/readline.html
        #
        # Note: This hack does not work well in Windows (see #5059)
        escape = codes.get(name, '')
        if input_mode and escape and sys.platform != 'win32':
            return '\1' + escape + '\2'
        else:
            return escape

    return escseq(name) + text + escseq('reset')


def strip_colors(s):
    # type: (str) -> str
    return re.compile('\x1b.*?m').sub('', s)


def create_color_func(name):
    # type: (str) -> None
    def inner(text):
        # type: (unicode) -> unicode
        return colorize(name, text)
    globals()[name] = inner


_attrs = {
    'reset':     '39;49;00m',
    'bold':      '01m',
    'faint':     '02m',
    'standout':  '03m',
    'underline': '04m',
    'blink':     '05m',
}

for _name, _value in _attrs.items():
    codes[_name] = '\x1b[' + _value

_colors = [
    ('black',     'darkgray'),
    ('darkred',   'red'),
    ('darkgreen', 'green'),
    ('brown',     'yellow'),
    ('darkblue',  'blue'),
    ('purple',    'fuchsia'),
    ('turquoise', 'teal'),
    ('lightgray', 'white'),
]

for i, (dark, light) in enumerate(_colors):
    codes[dark] = '\x1b[%im' % (i + 30)
    codes[light] = '\x1b[%i;01m' % (i + 30)

_orig_codes = codes.copy()

for _name in codes:
    create_color_func(_name)
