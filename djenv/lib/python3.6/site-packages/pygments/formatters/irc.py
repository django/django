# -*- coding: utf-8 -*-
"""
    pygments.formatters.irc
    ~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for IRC output

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys

from pygments.formatter import Formatter
from pygments.token import Keyword, Name, Comment, String, Error, \
    Number, Operator, Generic, Token, Whitespace
from pygments.util import get_choice_opt


__all__ = ['IRCFormatter']


#: Map token types to a tuple of color values for light and dark
#: backgrounds.
IRC_COLORS = {
    Token:              ('',            ''),

    Whitespace:         ('lightgray',   'darkgray'),
    Comment:            ('lightgray',   'darkgray'),
    Comment.Preproc:    ('teal',        'turquoise'),
    Keyword:            ('darkblue',    'blue'),
    Keyword.Type:       ('teal',        'turquoise'),
    Operator.Word:      ('purple',      'fuchsia'),
    Name.Builtin:       ('teal',        'turquoise'),
    Name.Function:      ('darkgreen',   'green'),
    Name.Namespace:     ('_teal_',      '_turquoise_'),
    Name.Class:         ('_darkgreen_', '_green_'),
    Name.Exception:     ('teal',        'turquoise'),
    Name.Decorator:     ('darkgray',    'lightgray'),
    Name.Variable:      ('darkred',     'red'),
    Name.Constant:      ('darkred',     'red'),
    Name.Attribute:     ('teal',        'turquoise'),
    Name.Tag:           ('blue',        'blue'),
    String:             ('brown',       'brown'),
    Number:             ('darkblue',    'blue'),

    Generic.Deleted:    ('red',        'red'),
    Generic.Inserted:   ('darkgreen',  'green'),
    Generic.Heading:    ('**',         '**'),
    Generic.Subheading: ('*purple*',   '*fuchsia*'),
    Generic.Error:      ('red',        'red'),

    Error:              ('_red_',      '_red_'),
}


IRC_COLOR_MAP = {
    'white': 0,
    'black': 1,
    'darkblue': 2,
    'green': 3,
    'red': 4,
    'brown': 5,
    'purple': 6,
    'orange': 7,
    'darkgreen': 7, #compat w/ ansi
    'yellow': 8,
    'lightgreen': 9,
    'turquoise': 9, # compat w/ ansi
    'teal': 10,
    'lightblue': 11,
    'darkred': 11, # compat w/ ansi
    'blue': 12,
    'fuchsia': 13,
    'darkgray': 14,
    'lightgray': 15,
}

def ircformat(color, text):
    if len(color) < 1:
        return text
    add = sub = ''
    if '_' in color: # italic
        add += '\x1D'
        sub = '\x1D' + sub
        color = color.strip('_')
    if '*' in color: # bold
        add += '\x02'
        sub = '\x02' + sub
        color = color.strip('*')
    # underline (\x1F) not supported
    # backgrounds (\x03FF,BB) not supported
    if len(color) > 0: # actual color - may have issues with ircformat("red", "blah")+"10" type stuff
        add += '\x03' + str(IRC_COLOR_MAP[color]).zfill(2)
        sub = '\x03' + sub
    return add + text + sub
    return '<'+add+'>'+text+'</'+sub+'>'


class IRCFormatter(Formatter):
    r"""
    Format tokens with IRC color sequences

    The `get_style_defs()` method doesn't do anything special since there is
    no support for common styles.

    Options accepted:

    `bg`
        Set to ``"light"`` or ``"dark"`` depending on the terminal's background
        (default: ``"light"``).

    `colorscheme`
        A dictionary mapping token types to (lightbg, darkbg) color names or
        ``None`` (default: ``None`` = use builtin colorscheme).

    `linenos`
        Set to ``True`` to have line numbers in the output as well
        (default: ``False`` = no line numbers).
    """
    name = 'IRC'
    aliases = ['irc', 'IRC']
    filenames = []

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.darkbg = get_choice_opt(options, 'bg',
                                     ['light', 'dark'], 'light') == 'dark'
        self.colorscheme = options.get('colorscheme', None) or IRC_COLORS
        self.linenos = options.get('linenos', False)
        self._lineno = 0

    def _write_lineno(self, outfile):
        self._lineno += 1
        outfile.write("\n%04d: " % self._lineno)

    def _format_unencoded_with_lineno(self, tokensource, outfile):
        self._write_lineno(outfile)

        for ttype, value in tokensource:
            if value.endswith("\n"):
                self._write_lineno(outfile)
                value = value[:-1]
            color = self.colorscheme.get(ttype)
            while color is None:
                ttype = ttype[:-1]
                color = self.colorscheme.get(ttype)
            if color:
                color = color[self.darkbg]
                spl = value.split('\n')
                for line in spl[:-1]:
                    self._write_lineno(outfile)
                    if line:
                        outfile.write(ircformat(color, line[:-1]))
                if spl[-1]:
                    outfile.write(ircformat(color, spl[-1]))
            else:
                outfile.write(value)

        outfile.write("\n")

    def format_unencoded(self, tokensource, outfile):
        if self.linenos:
            self._format_unencoded_with_lineno(tokensource, outfile)
            return

        for ttype, value in tokensource:
            color = self.colorscheme.get(ttype)
            while color is None:
                ttype = ttype[:-1]
                color = self.colorscheme.get(ttype)
            if color:
                color = color[self.darkbg]
                spl = value.split('\n')
                for line in spl[:-1]:
                    if line:
                        outfile.write(ircformat(color, line))
                    outfile.write('\n')
                if spl[-1]:
                    outfile.write(ircformat(color, spl[-1]))
            else:
                outfile.write(value)
