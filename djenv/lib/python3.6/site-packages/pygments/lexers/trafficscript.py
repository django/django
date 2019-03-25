# -*- coding: utf-8 -*-
"""
    pygments.lexers.trafficscript
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexer for RiverBed's TrafficScript (RTS) language.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer
from pygments.token import String, Number, Name, Keyword, Operator, Text, Comment

__all__ = ['RtsLexer']


class RtsLexer(RegexLexer):
    """
    For `Riverbed Stingray Traffic Manager <http://www.riverbed.com/stingray>`_

    .. versionadded:: 2.1
    """
    name = 'TrafficScript'
    aliases = ['rts','trafficscript']
    filenames = ['*.rts']

    tokens = {
        'root' : [
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String),
            (r'"', String, 'escapable-string'),
            (r'(0x[0-9a-fA-F]+|\d+)', Number),
            (r'\d+\.\d+', Number.Float),
            (r'\$[a-zA-Z](\w|_)*', Name.Variable),
            (r'(if|else|for(each)?|in|while|do|break|sub|return|import)', Keyword),
            (r'[a-zA-Z][\w.]*', Name.Function),
            (r'[-+*/%=,;(){}<>^.!~|&\[\]\?\:]', Operator),
            (r'(>=|<=|==|!=|'
             r'&&|\|\||'
             r'\+=|.=|-=|\*=|/=|%=|<<=|>>=|&=|\|=|\^=|'
             r'>>|<<|'
             r'\+\+|--|=>)', Operator),
            (r'[ \t\r]+', Text),
            (r'#[^\n]*', Comment),
        ],
        'escapable-string' : [
            (r'\\[tsn]', String.Escape),
            (r'[^"]', String),
            (r'"', String, '#pop'),
        ],

    }
