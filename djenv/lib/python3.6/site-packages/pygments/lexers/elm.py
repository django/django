# -*- coding: utf-8 -*-
"""
    pygments.lexers.elm
    ~~~~~~~~~~~~~~~~~~~

    Lexer for the Elm programming language.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, words, include
from pygments.token import Comment, Keyword, Name, Number, Punctuation, String, Text

__all__ = ['ElmLexer']


class ElmLexer(RegexLexer):
    """
    For `Elm <http://elm-lang.org/>`_ source code.

    .. versionadded:: 2.1
    """

    name = 'Elm'
    aliases = ['elm']
    filenames = ['*.elm']
    mimetypes = ['text/x-elm']

    validName = r'[a-z_][a-zA-Z0-9_\']*'

    specialName = r'^main '

    builtinOps = (
        '~', '||', '|>', '|', '`', '^', '\\', '\'', '>>', '>=', '>', '==',
        '=', '<~', '<|', '<=', '<<', '<-', '<', '::', ':', '/=', '//', '/',
        '..', '.', '->', '-', '++', '+', '*', '&&', '%',
    )

    reservedWords = words((
        'alias', 'as', 'case', 'else', 'if', 'import', 'in',
        'let', 'module', 'of', 'port', 'then', 'type', 'where',
        ), suffix=r'\b')

    tokens = {
        'root': [

            # Comments
            (r'\{-', Comment.Multiline, 'comment'),
            (r'--.*', Comment.Single),

            # Whitespace
            (r'\s+', Text),

            # Strings
            (r'"', String, 'doublequote'),

            # Modules
            (r'^\s*module\s*', Keyword.Namespace, 'imports'),

            # Imports
            (r'^\s*import\s*', Keyword.Namespace, 'imports'),

            # Shaders
            (r'\[glsl\|.*', Name.Entity, 'shader'),

            # Keywords
            (reservedWords, Keyword.Reserved),

            # Types
            (r'[A-Z]\w*', Keyword.Type),

            # Main
            (specialName, Keyword.Reserved),

            # Prefix Operators
            (words((builtinOps), prefix=r'\(', suffix=r'\)'), Name.Function),

            # Infix Operators
            (words((builtinOps)), Name.Function),

            # Numbers
            include('numbers'),

            # Variable Names
            (validName, Name.Variable),

            # Parens
            (r'[,()\[\]{}]', Punctuation),

        ],

        'comment': [
            (r'-(?!\})', Comment.Multiline),
            (r'\{-', Comment.Multiline, 'comment'),
            (r'[^-}]', Comment.Multiline),
            (r'-\}', Comment.Multiline, '#pop'),
        ],

        'doublequote': [
            (r'\\u[0-9a-fA-F]{4}', String.Escape),
            (r'\\[nrfvb\\"]', String.Escape),
            (r'[^"]', String),
            (r'"', String, '#pop'),
        ],

        'imports': [
            (r'\w+(\.\w+)*', Name.Class, '#pop'),
        ],

        'numbers': [
            (r'_?\d+\.(?=\d+)', Number.Float),
            (r'_?\d+', Number.Integer),
        ],

        'shader': [
            (r'\|(?!\])', Name.Entity),
            (r'\|\]', Name.Entity, '#pop'),
            (r'.*\n', Name.Entity),
        ],
    }
