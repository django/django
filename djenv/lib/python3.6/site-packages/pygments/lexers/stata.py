# -*- coding: utf-8 -*-
"""
    pygments.lexers.stata
    ~~~~~~~~~~~~~~~~~~~~~

    Lexer for Stata

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, include, words
from pygments.token import Comment, Keyword, Name, Number, \
    String, Text, Operator

from pygments.lexers._stata_builtins import builtins_base, builtins_functions

__all__ = ['StataLexer']


class StataLexer(RegexLexer):
    """
    For `Stata <http://www.stata.com/>`_ do files.

    .. versionadded:: 2.2
    """
    # Syntax based on
    # - http://fmwww.bc.edu/RePEc/bocode/s/synlightlist.ado
    # - http://github.com/isagalaev/highlight.js/blob/master/src/languages/stata.js
    # - http://github.com/jpitblado/vim-stata/blob/master/syntax/stata.vim

    name      = 'Stata'
    aliases   = ['stata', 'do']
    filenames = ['*.do', '*.ado']
    mimetypes = ['text/x-stata', 'text/stata', 'application/x-stata']

    tokens = {
        'root': [
            include('comments'),
            include('vars-strings'),
            include('numbers'),
            include('keywords'),
            (r'.', Text),
        ],
        # Global and local macros; regular and special strings
        'vars-strings': [
            (r'\$[\w{]', Name.Variable.Global, 'var_validglobal'),
            (r'`\w{0,31}\'', Name.Variable),
            (r'"', String, 'string_dquote'),
            (r'`"', String, 'string_mquote'),
        ],
        # For either string type, highlight macros as macros
        'string_dquote': [
            (r'"', String, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),
            (r'\$', Name.Variable.Global, 'var_validglobal'),
            (r'`', Name.Variable, 'var_validlocal'),
            (r'[^$`"\\]+', String),
            (r'[$"\\]', String),
        ],
        'string_mquote': [
            (r'"\'', String, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),
            (r'\$', Name.Variable.Global, 'var_validglobal'),
            (r'`', Name.Variable, 'var_validlocal'),
            (r'[^$`"\\]+', String),
            (r'[$"\\]', String),
        ],
        'var_validglobal': [
            (r'\{\w{0,32}\}', Name.Variable.Global, '#pop'),
            (r'\w{1,32}', Name.Variable.Global, '#pop'),
        ],
        'var_validlocal': [
            (r'\w{0,31}\'', Name.Variable, '#pop'),
        ],
        # * only OK at line start, // OK anywhere
        'comments': [
            (r'^\s*\*.*$', Comment),
            (r'//.*', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'/[*](.|\n)*?[*]/', Comment.Multiline),
        ],
        # Built in functions and statements
        'keywords': [
            (words(builtins_functions, prefix = r'\b', suffix = r'\('),
             Name.Function),
            (words(builtins_base, prefix = r'(^\s*|\s)', suffix = r'\b'),
             Keyword),
        ],
        # http://www.stata.com/help.cgi?operators
        'operators': [
            (r'-|==|<=|>=|<|>|&|!=', Operator),
            (r'\*|\+|\^|/|!|~|==|~=', Operator)
        ],
        # Stata numbers
        'numbers': [
            # decimal number
            (r'\b[+-]?([0-9]+(\.[0-9]+)?|\.[0-9]+|\.)([eE][+-]?[0-9]+)?[i]?\b',
             Number),
        ],
        # Stata formats
        'format': [
            (r'%-?\d{1,2}(\.\d{1,2})?[gfe]c?', Name.Variable),
            (r'%(21x|16H|16L|8H|8L)', Name.Variable),
            (r'%-?(tc|tC|td|tw|tm|tq|th|ty|tg).{0,32}', Name.Variable),
            (r'%[-~]?\d{1,4}s', Name.Variable),
        ]
    }
