# -*- coding: utf-8 -*-
"""
    pygments.lexers.nimrod
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexer for the Nim language (formerly known as Nimrod).

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, default
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Error

__all__ = ['NimrodLexer']


class NimrodLexer(RegexLexer):
    """
    For `Nim <http://nim-lang.org/>`_ source code.

    .. versionadded:: 1.5
    """

    name = 'Nimrod'
    aliases = ['nim', 'nimrod']
    filenames = ['*.nim', '*.nimrod']
    mimetypes = ['text/x-nim']

    flags = re.MULTILINE | re.IGNORECASE | re.UNICODE

    def underscorize(words):
        newWords = []
        new = ""
        for word in words:
            for ch in word:
                new += (ch + "_?")
            newWords.append(new)
            new = ""
        return "|".join(newWords)

    keywords = [
        'addr', 'and', 'as', 'asm', 'atomic', 'bind', 'block', 'break', 'case',
        'cast', 'concept', 'const', 'continue', 'converter', 'defer', 'discard',
        'distinct', 'div', 'do', 'elif', 'else', 'end', 'enum', 'except',
        'export', 'finally', 'for', 'func', 'if', 'in', 'yield', 'interface',
        'is', 'isnot', 'iterator', 'let', 'macro', 'method', 'mixin', 'mod',
        'not', 'notin', 'object', 'of', 'or', 'out', 'proc', 'ptr', 'raise',
        'ref', 'return', 'shared', 'shl', 'shr', 'static', 'template', 'try',
        'tuple', 'type', 'when', 'while', 'with', 'without', 'xor'
    ]

    keywordsPseudo = [
        'nil', 'true', 'false'
    ]

    opWords = [
        'and', 'or', 'not', 'xor', 'shl', 'shr', 'div', 'mod', 'in',
        'notin', 'is', 'isnot'
    ]

    types = [
        'int', 'int8', 'int16', 'int32', 'int64', 'float', 'float32', 'float64',
        'bool', 'char', 'range', 'array', 'seq', 'set', 'string'
    ]

    tokens = {
        'root': [
            (r'##.*$', String.Doc),
            (r'#.*$', Comment),
            (r'[*=><+\-/@$~&%!?|\\\[\]]', Operator),
            (r'\.\.|\.|,|\[\.|\.\]|\{\.|\.\}|\(\.|\.\)|\{|\}|\(|\)|:|\^|`|;',
             Punctuation),

            # Strings
            (r'(?:[\w]+)"', String, 'rdqs'),
            (r'"""', String, 'tdqs'),
            ('"', String, 'dqs'),

            # Char
            ("'", String.Char, 'chars'),

            # Keywords
            (r'(%s)\b' % underscorize(opWords), Operator.Word),
            (r'(p_?r_?o_?c_?\s)(?![(\[\]])', Keyword, 'funcname'),
            (r'(%s)\b' % underscorize(keywords), Keyword),
            (r'(%s)\b' % underscorize(['from', 'import', 'include']),
             Keyword.Namespace),
            (r'(v_?a_?r)\b', Keyword.Declaration),
            (r'(%s)\b' % underscorize(types), Keyword.Type),
            (r'(%s)\b' % underscorize(keywordsPseudo), Keyword.Pseudo),
            # Identifiers
            (r'\b((?![_\d])\w)(((?!_)\w)|(_(?!_)\w))*', Name),
            # Numbers
            (r'[0-9][0-9_]*(?=([e.]|\'f(32|64)))',
             Number.Float, ('float-suffix', 'float-number')),
            (r'0x[a-f0-9][a-f0-9_]*', Number.Hex, 'int-suffix'),
            (r'0b[01][01_]*', Number.Bin, 'int-suffix'),
            (r'0o[0-7][0-7_]*', Number.Oct, 'int-suffix'),
            (r'[0-9][0-9_]*', Number.Integer, 'int-suffix'),
            # Whitespace
            (r'\s+', Text),
            (r'.+$', Error),
        ],
        'chars': [
            (r'\\([\\abcefnrtvl"\']|x[a-f0-9]{2}|[0-9]{1,3})', String.Escape),
            (r"'", String.Char, '#pop'),
            (r".", String.Char)
        ],
        'strings': [
            (r'(?<!\$)\$(\d+|#|\w+)+', String.Interpol),
            (r'[^\\\'"$\n]+', String),
            # quotes, dollars and backslashes must be parsed one at a time
            (r'[\'"\\]', String),
            # unhandled string formatting sign
            (r'\$', String)
            # newlines are an error (use "nl" state)
        ],
        'dqs': [
            (r'\\([\\abcefnrtvl"\']|\n|x[a-f0-9]{2}|[0-9]{1,3})',
             String.Escape),
            (r'"', String, '#pop'),
            include('strings')
        ],
        'rdqs': [
            (r'"(?!")', String, '#pop'),
            (r'""', String.Escape),
            include('strings')
        ],
        'tdqs': [
            (r'"""(?!")', String, '#pop'),
            include('strings'),
            include('nl')
        ],
        'funcname': [
            (r'((?![\d_])\w)(((?!_)\w)|(_(?!_)\w))*', Name.Function, '#pop'),
            (r'`.+`', Name.Function, '#pop')
        ],
        'nl': [
            (r'\n', String)
        ],
        'float-number': [
            (r'\.(?!\.)[0-9_]*', Number.Float),
            (r'e[+-]?[0-9][0-9_]*', Number.Float),
            default('#pop')
        ],
        'float-suffix': [
            (r'\'f(32|64)', Number.Float),
            default('#pop')
        ],
        'int-suffix': [
            (r'\'i(32|64)', Number.Integer.Long),
            (r'\'i(8|16)', Number.Integer),
            default('#pop')
        ],
    }
