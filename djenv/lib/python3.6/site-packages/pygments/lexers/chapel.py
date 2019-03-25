# -*- coding: utf-8 -*-
"""
    pygments.lexers.chapel
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexer for the Chapel language.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, bygroups, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation

__all__ = ['ChapelLexer']


class ChapelLexer(RegexLexer):
    """
    For `Chapel <http://chapel.cray.com/>`_ source.

    .. versionadded:: 2.0
    """
    name = 'Chapel'
    filenames = ['*.chpl']
    aliases = ['chapel', 'chpl']
    # mimetypes = ['text/x-chapel']

    tokens = {
        'root': [
            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text),

            (r'//(.*?)\n', Comment.Single),
            (r'/(\\\n)?[*](.|\n)*?[*](\\\n)?/', Comment.Multiline),

            (r'(config|const|in|inout|out|param|ref|type|var)\b',
             Keyword.Declaration),
            (r'(false|nil|true)\b', Keyword.Constant),
            (r'(bool|complex|imag|int|opaque|range|real|string|uint)\b',
             Keyword.Type),
            (words((
                'align', 'as', 'atomic',
                'begin', 'borrowed', 'break', 'by',
                'catch', 'cobegin', 'coforall', 'continue',
                'delete', 'dmapped', 'do', 'domain',
                'else', 'enum', 'except', 'export', 'extern',
                'for', 'forall',
                'if', 'index', 'inline',
                'label', 'lambda', 'let', 'local',
                'new', 'noinit',
                'on', 'only', 'otherwise', 'override', 'owned',
                'pragma', 'private', 'prototype', 'public',
                'reduce', 'require', 'return',
                'scan', 'select', 'serial', 'shared', 'single', 'sparse', 'subdomain', 'sync',
                'then', 'throw', 'throws', 'try',
                'unmanaged', 'use',
                'when', 'where', 'while', 'with',
                'yield',
                'zip'), suffix=r'\b'),
             Keyword),
            (r'(iter)((?:\s)+)', bygroups(Keyword, Text), 'procname'),
            (r'(proc)((?:\s)+)', bygroups(Keyword, Text), 'procname'),
            (r'(class|module|record|union)(\s+)', bygroups(Keyword, Text),
             'classname'),

            # imaginary integers
            (r'\d+i', Number),
            (r'\d+\.\d*([Ee][-+]\d+)?i', Number),
            (r'\.\d+([Ee][-+]\d+)?i', Number),
            (r'\d+[Ee][-+]\d+i', Number),

            # reals cannot end with a period due to lexical ambiguity with
            # .. operator. See reference for rationale.
            (r'(\d*\.\d+)([eE][+-]?[0-9]+)?i?', Number.Float),
            (r'\d+[eE][+-]?[0-9]+i?', Number.Float),

            # integer literals
            # -- binary
            (r'0[bB][01]+', Number.Bin),
            # -- hex
            (r'0[xX][0-9a-fA-F]+', Number.Hex),
            # -- octal
            (r'0[oO][0-7]+', Number.Oct),
            # -- decimal
            (r'[0-9]+', Number.Integer),

            # strings
            (r'"(\\\\|\\"|[^"])*"', String),
            (r"'(\\\\|\\'|[^'])*'", String),

            # tokens
            (r'(=|\+=|-=|\*=|/=|\*\*=|%=|&=|\|=|\^=|&&=|\|\|=|<<=|>>=|'
             r'<=>|<~>|\.\.|by|#|\.\.\.|'
             r'&&|\|\||!|&|\||\^|~|<<|>>|'
             r'==|!=|<=|>=|<|>|'
             r'[+\-*/%]|\*\*)', Operator),
            (r'[:;,.?()\[\]{}]', Punctuation),

            # identifiers
            (r'[a-zA-Z_][\w$]*', Name.Other),
        ],
        'classname': [
            (r'[a-zA-Z_][\w$]*', Name.Class, '#pop'),
        ],
        'procname': [
            (r'([a-zA-Z_][.\w$]*|\~[a-zA-Z_][.\w$]*|[+*/!~%<>=&^|\-]{1,2})',
             Name.Function, '#pop'),
        ],
    }
