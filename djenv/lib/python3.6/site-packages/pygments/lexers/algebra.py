# -*- coding: utf-8 -*-
"""
    pygments.lexers.algebra
    ~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for computer algebra systems.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, bygroups, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation

__all__ = ['GAPLexer', 'MathematicaLexer', 'MuPADLexer', 'BCLexer']


class GAPLexer(RegexLexer):
    """
    For `GAP <http://www.gap-system.org>`_ source code.

    .. versionadded:: 2.0
    """
    name = 'GAP'
    aliases = ['gap']
    filenames = ['*.g', '*.gd', '*.gi', '*.gap']

    tokens = {
        'root': [
            (r'#.*$', Comment.Single),
            (r'"(?:[^"\\]|\\.)*"', String),
            (r'\(|\)|\[|\]|\{|\}', Punctuation),
            (r'''(?x)\b(?:
                if|then|elif|else|fi|
                for|while|do|od|
                repeat|until|
                break|continue|
                function|local|return|end|
                rec|
                quit|QUIT|
                IsBound|Unbind|
                TryNextMethod|
                Info|Assert
              )\b''', Keyword),
            (r'''(?x)\b(?:
                true|false|fail|infinity
              )\b''',
             Name.Constant),
            (r'''(?x)\b(?:
                (Declare|Install)([A-Z][A-Za-z]+)|
                   BindGlobal|BIND_GLOBAL
              )\b''',
             Name.Builtin),
            (r'\.|,|:=|;|=|\+|-|\*|/|\^|>|<', Operator),
            (r'''(?x)\b(?:
                and|or|not|mod|in
              )\b''',
             Operator.Word),
            (r'''(?x)
              (?:\w+|`[^`]*`)
              (?:::\w+|`[^`]*`)*''', Name.Variable),
            (r'[0-9]+(?:\.[0-9]*)?(?:e[0-9]+)?', Number),
            (r'\.[0-9]+(?:e[0-9]+)?', Number),
            (r'.', Text)
        ],
    }


class MathematicaLexer(RegexLexer):
    """
    Lexer for `Mathematica <http://www.wolfram.com/mathematica/>`_ source code.

    .. versionadded:: 2.0
    """
    name = 'Mathematica'
    aliases = ['mathematica', 'mma', 'nb']
    filenames = ['*.nb', '*.cdf', '*.nbp', '*.ma']
    mimetypes = ['application/mathematica',
                 'application/vnd.wolfram.mathematica',
                 'application/vnd.wolfram.mathematica.package',
                 'application/vnd.wolfram.cdf']

    # http://reference.wolfram.com/mathematica/guide/Syntax.html
    operators = (
        ";;", "=", "=.", "!=" "==", ":=", "->", ":>", "/.", "+", "-", "*", "/",
        "^", "&&", "||", "!", "<>", "|", "/;", "?", "@", "//", "/@", "@@",
        "@@@", "~~", "===", "&", "<", ">", "<=", ">=",
    )

    punctuation = (",", ";", "(", ")", "[", "]", "{", "}")

    def _multi_escape(entries):
        return '(%s)' % ('|'.join(re.escape(entry) for entry in entries))

    tokens = {
        'root': [
            (r'(?s)\(\*.*?\*\)', Comment),

            (r'([a-zA-Z]+[A-Za-z0-9]*`)', Name.Namespace),
            (r'([A-Za-z0-9]*_+[A-Za-z0-9]*)', Name.Variable),
            (r'#\d*', Name.Variable),
            (r'([a-zA-Z]+[a-zA-Z0-9]*)', Name),

            (r'-?\d+\.\d*', Number.Float),
            (r'-?\d*\.\d+', Number.Float),
            (r'-?\d+', Number.Integer),

            (words(operators), Operator),
            (words(punctuation), Punctuation),
            (r'".*?"', String),
            (r'\s+', Text.Whitespace),
        ],
    }


class MuPADLexer(RegexLexer):
    """
    A `MuPAD <http://www.mupad.com>`_ lexer.
    Contributed by Christopher Creutzig <christopher@creutzig.de>.

    .. versionadded:: 0.8
    """
    name = 'MuPAD'
    aliases = ['mupad']
    filenames = ['*.mu']

    tokens = {
        'root': [
            (r'//.*?$', Comment.Single),
            (r'/\*', Comment.Multiline, 'comment'),
            (r'"(?:[^"\\]|\\.)*"', String),
            (r'\(|\)|\[|\]|\{|\}', Punctuation),
            (r'''(?x)\b(?:
                next|break|end|
                axiom|end_axiom|category|end_category|domain|end_domain|inherits|
                if|%if|then|elif|else|end_if|
                case|of|do|otherwise|end_case|
                while|end_while|
                repeat|until|end_repeat|
                for|from|to|downto|step|end_for|
                proc|local|option|save|begin|end_proc|
                delete|frame
              )\b''', Keyword),
            (r'''(?x)\b(?:
                DOM_ARRAY|DOM_BOOL|DOM_COMPLEX|DOM_DOMAIN|DOM_EXEC|DOM_EXPR|
                DOM_FAIL|DOM_FLOAT|DOM_FRAME|DOM_FUNC_ENV|DOM_HFARRAY|DOM_IDENT|
                DOM_INT|DOM_INTERVAL|DOM_LIST|DOM_NIL|DOM_NULL|DOM_POLY|DOM_PROC|
                DOM_PROC_ENV|DOM_RAT|DOM_SET|DOM_STRING|DOM_TABLE|DOM_VAR
              )\b''', Name.Class),
            (r'''(?x)\b(?:
                PI|EULER|E|CATALAN|
                NIL|FAIL|undefined|infinity|
                TRUE|FALSE|UNKNOWN
              )\b''',
             Name.Constant),
            (r'\b(?:dom|procname)\b', Name.Builtin.Pseudo),
            (r'\.|,|:|;|=|\+|-|\*|/|\^|@|>|<|\$|\||!|\'|%|~=', Operator),
            (r'''(?x)\b(?:
                and|or|not|xor|
                assuming|
                div|mod|
                union|minus|intersect|in|subset
              )\b''',
             Operator.Word),
            (r'\b(?:I|RDN_INF|RD_NINF|RD_NAN)\b', Number),
            # (r'\b(?:adt|linalg|newDomain|hold)\b', Name.Builtin),
            (r'''(?x)
              ((?:[a-zA-Z_#][\w#]*|`[^`]*`)
              (?:::[a-zA-Z_#][\w#]*|`[^`]*`)*)(\s*)([(])''',
             bygroups(Name.Function, Text, Punctuation)),
            (r'''(?x)
              (?:[a-zA-Z_#][\w#]*|`[^`]*`)
              (?:::[a-zA-Z_#][\w#]*|`[^`]*`)*''', Name.Variable),
            (r'[0-9]+(?:\.[0-9]*)?(?:e[0-9]+)?', Number),
            (r'\.[0-9]+(?:e[0-9]+)?', Number),
            (r'.', Text)
        ],
        'comment': [
            (r'[^*/]', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline)
        ],
    }


class BCLexer(RegexLexer):
    """
    A `BC <https://www.gnu.org/software/bc/>`_ lexer.

    .. versionadded:: 2.1
    """
    name = 'BC'
    aliases = ['bc']
    filenames = ['*.bc']

    tokens = {
        'root': [
            (r'/\*', Comment.Multiline, 'comment'),
            (r'"(?:[^"\\]|\\.)*"', String),
            (r'[{}();,]', Punctuation),
            (words(('if', 'else', 'while', 'for', 'break', 'continue',
                    'halt', 'return', 'define', 'auto', 'print', 'read',
                    'length', 'scale', 'sqrt', 'limits', 'quit',
                    'warranty'), suffix=r'\b'), Keyword),
            (r'\+\+|--|\|\||&&|'
             r'([-<>+*%\^/!=])=?', Operator),
            # bc doesn't support exponential
            (r'[0-9]+(\.[0-9]*)?', Number),
            (r'\.[0-9]+', Number),
            (r'.', Text)
        ],
        'comment': [
            (r'[^*/]+', Comment.Multiline),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline)
        ],
    }
