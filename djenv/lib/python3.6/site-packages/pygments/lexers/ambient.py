# -*- coding: utf-8 -*-
"""
    pygments.lexers.ambient
    ~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for AmbientTalk language.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation

__all__ = ['AmbientTalkLexer']


class AmbientTalkLexer(RegexLexer):
    """
    Lexer for `AmbientTalk <https://code.google.com/p/ambienttalk>`_ source code.

    .. versionadded:: 2.0
    """
    name = 'AmbientTalk'
    filenames = ['*.at']
    aliases = ['at', 'ambienttalk', 'ambienttalk/2']
    mimetypes = ['text/x-ambienttalk']

    flags = re.MULTILINE | re.DOTALL

    builtin = words(('if:', 'then:', 'else:', 'when:', 'whenever:', 'discovered:',
                     'disconnected:', 'reconnected:', 'takenOffline:', 'becomes:',
                     'export:', 'as:', 'object:', 'actor:', 'mirror:', 'taggedAs:',
                     'mirroredBy:', 'is:'))
    tokens = {
        'root': [
            (r'\s+', Text),
            (r'//.*?\n', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'(def|deftype|import|alias|exclude)\b', Keyword),
            (builtin, Name.Builtin),
            (r'(true|false|nil)\b', Keyword.Constant),
            (r'(~|lobby|jlobby|/)\.', Keyword.Constant, 'namespace'),
            (r'"(\\\\|\\"|[^"])*"', String),
            (r'\|', Punctuation, 'arglist'),
            (r'<:|[*^!%&<>+=,./?-]|:=', Operator),
            (r"`[a-zA-Z_]\w*", String.Symbol),
            (r"[a-zA-Z_]\w*:", Name.Function),
            (r"[{}()\[\];`]", Punctuation),
            (r'(self|super)\b', Name.Variable.Instance),
            (r"[a-zA-Z_]\w*", Name.Variable),
            (r"@[a-zA-Z_]\w*", Name.Class),
            (r"@\[", Name.Class, 'annotations'),
            include('numbers'),
        ],
        'numbers': [
            (r'(\d+\.\d*|\d*\.\d+)([eE][+-]?[0-9]+)?', Number.Float),
            (r'\d+', Number.Integer)
        ],
        'namespace': [
            (r'[a-zA-Z_]\w*\.', Name.Namespace),
            (r'[a-zA-Z_]\w*:', Name.Function, '#pop'),
            (r'[a-zA-Z_]\w*(?!\.)', Name.Function, '#pop')
        ],
        'annotations': [
            (r"(.*?)\]", Name.Class, '#pop')
        ],
        'arglist': [
            (r'\|', Punctuation, '#pop'),
            (r'\s*(,)\s*', Punctuation),
            (r'[a-zA-Z_]\w*', Name.Variable),
        ],
    }
