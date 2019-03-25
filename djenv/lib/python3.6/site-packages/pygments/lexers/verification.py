# -*- coding: utf-8 -*-
"""
    pygments.lexers.verification
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexer for Intermediate Verification Languages (IVLs).

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, include, words
from pygments.token import Comment, Operator, Keyword, Name, Number, \
    Punctuation, Whitespace

__all__ = ['BoogieLexer', 'SilverLexer']


class BoogieLexer(RegexLexer):
    """
    For `Boogie <https://boogie.codeplex.com/>`_ source code.

    .. versionadded:: 2.1
    """
    name = 'Boogie'
    aliases = ['boogie']
    filenames = ['*.bpl']

    tokens = {
        'root': [
            # Whitespace and Comments
            (r'\n', Whitespace),
            (r'\s+', Whitespace),
            (r'//[/!](.*?)\n', Comment.Doc),
            (r'//(.*?)\n', Comment.Single),
            (r'/\*', Comment.Multiline, 'comment'),

            (words((
                'axiom', 'break', 'call', 'ensures', 'else', 'exists', 'function',
                'forall', 'if', 'invariant', 'modifies', 'procedure',  'requires',
                'then', 'var', 'while'),
             suffix=r'\b'), Keyword),
            (words(('const',), suffix=r'\b'), Keyword.Reserved),

            (words(('bool', 'int', 'ref'), suffix=r'\b'), Keyword.Type),
            include('numbers'),
            (r"(>=|<=|:=|!=|==>|&&|\|\||[+/\-=>*<\[\]])", Operator),
            (r"([{}():;,.])", Punctuation),
            # Identifier
            (r'[a-zA-Z_]\w*', Name),
        ],
        'comment': [
            (r'[^*/]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline),
        ],
        'numbers': [
            (r'[0-9]+', Number.Integer),
        ],
    }


class SilverLexer(RegexLexer):
    """
    For `Silver <https://bitbucket.org/viperproject/silver>`_ source code.

    .. versionadded:: 2.2
    """
    name = 'Silver'
    aliases = ['silver']
    filenames = ['*.sil', '*.vpr']

    tokens = {
        'root': [
            # Whitespace and Comments
            (r'\n', Whitespace),
            (r'\s+', Whitespace),
            (r'//[/!](.*?)\n', Comment.Doc),
            (r'//(.*?)\n', Comment.Single),
            (r'/\*', Comment.Multiline, 'comment'),

            (words((
                'result', 'true', 'false', 'null', 'method', 'function',
                'predicate', 'program', 'domain', 'axiom', 'var', 'returns',
                'field', 'define', 'requires', 'ensures', 'invariant',
                'fold', 'unfold', 'inhale', 'exhale', 'new', 'assert',
                'assume', 'goto', 'while', 'if', 'elseif', 'else', 'fresh',
                'constraining', 'Seq', 'Set', 'Multiset', 'union', 'intersection',
                'setminus', 'subset', 'unfolding', 'in', 'old', 'forall', 'exists',
                'acc', 'wildcard', 'write', 'none', 'epsilon', 'perm', 'unique',
                'apply', 'package', 'folding', 'label', 'forperm'),
             suffix=r'\b'), Keyword),
            (words(('Int', 'Perm', 'Bool', 'Ref'), suffix=r'\b'), Keyword.Type),
            include('numbers'),

            (r'[!%&*+=|?:<>/\-\[\]]', Operator),
            (r'([{}():;,.])', Punctuation),
            # Identifier
            (r'[\w$]\w*', Name),
        ],
        'comment': [
            (r'[^*/]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline),
        ],
        'numbers': [
            (r'[0-9]+', Number.Integer),
        ],
    }
