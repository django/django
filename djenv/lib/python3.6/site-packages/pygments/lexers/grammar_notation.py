# -*- coding: utf-8 -*-
"""
    pygments.lexers.grammar_notation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for grammer notations like BNF.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, bygroups, include, this, using, words
from pygments.token import Comment, Keyword, Literal, Name, Number, \
    Operator, Punctuation, String, Text

__all__ = ['BnfLexer', 'AbnfLexer', 'JsgfLexer']


class BnfLexer(RegexLexer):
    """
    This lexer is for grammer notations which are similar to
    original BNF.

    In order to maximize a number of targets of this lexer,
    let's decide some designs:

    * We don't distinguish `Terminal Symbol`.

    * We do assume that `NonTerminal Symbol` are always enclosed
      with arrow brackets.

    * We do assume that `NonTerminal Symbol` may include
      any printable characters except arrow brackets and ASCII 0x20.
      This assumption is for `RBNF <http://www.rfc-base.org/txt/rfc-5511.txt>`_.

    * We do assume that target notation doesn't support comment.

    * We don't distinguish any operators and punctuation except
      `::=`.

    Though these desision making might cause too minimal highlighting
    and you might be disappointed, but it is reasonable for us.

    .. versionadded:: 2.1
    """

    name = 'BNF'
    aliases = ['bnf']
    filenames = ['*.bnf']
    mimetypes = ['text/x-bnf']

    tokens = {
        'root': [
            (r'(<)([ -;=?-~]+)(>)',
             bygroups(Punctuation, Name.Class, Punctuation)),

            # an only operator
            (r'::=', Operator),

            # fallback
            (r'[^<>:]+', Text),  # for performance
            (r'.', Text),
        ],
    }


class AbnfLexer(RegexLexer):
    """
    Lexer for `IETF 7405 ABNF
    <http://www.ietf.org/rfc/rfc7405.txt>`_
    (Updates `5234 <http://www.ietf.org/rfc/rfc5234.txt>`_)
    grammars.

    .. versionadded:: 2.1
    """

    name = 'ABNF'
    aliases = ['abnf']
    filenames = ['*.abnf']
    mimetypes = ['text/x-abnf']

    _core_rules = (
        'ALPHA', 'BIT', 'CHAR', 'CR', 'CRLF', 'CTL', 'DIGIT',
        'DQUOTE', 'HEXDIG', 'HTAB', 'LF', 'LWSP', 'OCTET',
        'SP', 'VCHAR', 'WSP')

    tokens = {
        'root': [
            # comment
            (r';.*$', Comment.Single),

            # quoted
            #   double quote itself in this state, it is as '%x22'.
            (r'(%[si])?"[^"]*"', Literal),

            # binary (but i have never seen...)
            (r'%b[01]+\-[01]+\b', Literal),  # range
            (r'%b[01]+(\.[01]+)*\b', Literal),  # concat

            # decimal
            (r'%d[0-9]+\-[0-9]+\b', Literal),  # range
            (r'%d[0-9]+(\.[0-9]+)*\b', Literal),  # concat

            # hexadecimal
            (r'%x[0-9a-fA-F]+\-[0-9a-fA-F]+\b', Literal),  # range
            (r'%x[0-9a-fA-F]+(\.[0-9a-fA-F]+)*\b', Literal),  # concat

            # repetition (<a>*<b>element) including nRule
            (r'\b[0-9]+\*[0-9]+', Operator),
            (r'\b[0-9]+\*', Operator),
            (r'\b[0-9]+', Operator),
            (r'\*', Operator),

            # Strictly speaking, these are not keyword but
            # are called `Core Rule'.
            (words(_core_rules, suffix=r'\b'), Keyword),

            # nonterminals (ALPHA *(ALPHA / DIGIT / "-"))
            (r'[a-zA-Z][a-zA-Z0-9-]+\b', Name.Class),

            # operators
            (r'(=/|=|/)', Operator),

            # punctuation
            (r'[\[\]()]', Punctuation),

            # fallback
            (r'\s+', Text),
            (r'.', Text),
        ],
    }


class JsgfLexer(RegexLexer):
    """
    For `JSpeech Grammar Format <https://www.w3.org/TR/jsgf/>`_
    grammars.

    .. versionadded:: 2.2
    """
    name = 'JSGF'
    aliases = ['jsgf']
    filenames = ['*.jsgf']
    mimetypes = ['application/jsgf', 'application/x-jsgf', 'text/jsgf']

    flags = re.MULTILINE | re.UNICODE

    tokens = {
        'root': [
            include('comments'),
            include('non-comments'),
        ],
        'comments': [
            (r'/\*\*(?!/)', Comment.Multiline, 'documentation comment'),
            (r'/\*[\w\W]*?\*/', Comment.Multiline),
            (r'//.*', Comment.Single),
        ],
        'non-comments': [
            (r'\A#JSGF[^;]*', Comment.Preproc),
            (r'\s+', Text),
            (r';', Punctuation),
            (r'[=|()\[\]*+]', Operator),
            (r'/[^/]+/', Number.Float),
            (r'"', String.Double, 'string'),
            (r'\{', String.Other, 'tag'),
            (words(('import', 'public'), suffix=r'\b'), Keyword.Reserved),
            (r'grammar\b', Keyword.Reserved, 'grammar name'),
            (r'(<)(NULL|VOID)(>)',
             bygroups(Punctuation, Name.Builtin, Punctuation)),
            (r'<', Punctuation, 'rulename'),
            (r'\w+|[^\s;=|()\[\]*+/"{<\w]+', Text),
        ],
        'string': [
            (r'"', String.Double, '#pop'),
            (r'\\.', String.Escape),
            (r'[^\\"]+', String.Double),
        ],
        'tag': [
            (r'\}', String.Other, '#pop'),
            (r'\\.', String.Escape),
            (r'[^\\}]+', String.Other),
        ],
        'grammar name': [
            (r';', Punctuation, '#pop'),
            (r'\s+', Text),
            (r'\.', Punctuation),
            (r'[^;\s.]+', Name.Namespace),
        ],
        'rulename': [
            (r'>', Punctuation, '#pop'),
            (r'\*', Punctuation),
            (r'\s+', Text),
            (r'([^.>]+)(\s*)(\.)', bygroups(Name.Namespace, Text, Punctuation)),
            (r'[^.>]+', Name.Constant),
        ],
        'documentation comment': [
            (r'\*/', Comment.Multiline, '#pop'),
            (r'(^\s*\*?\s*)(@(?:example|see)\s+)'
             r'([\w\W]*?(?=(?:^\s*\*?\s*@|\*/)))',
             bygroups(Comment.Multiline, Comment.Special,
                      using(this, state='example'))),
            (r'(^\s*\*?\s*)(@\S*)',
             bygroups(Comment.Multiline, Comment.Special)),
            (r'[^*\n@]+|\w|\W', Comment.Multiline),
        ],
        'example': [
            (r'\n\s*\*', Comment.Multiline),
            include('non-comments'),
            (r'.', Comment.Multiline),
        ],
    }
