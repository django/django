# -*- coding: utf-8 -*-
"""
    pygments.lexers.rdf
    ~~~~~~~~~~~~~~~~~~~

    Lexers for semantic web and RDF query languages and markup.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, bygroups, default
from pygments.token import Keyword, Punctuation, String, Number, Operator, Generic, \
    Whitespace, Name, Literal, Comment, Text

__all__ = ['SparqlLexer', 'TurtleLexer']


class SparqlLexer(RegexLexer):
    """
    Lexer for `SPARQL <http://www.w3.org/TR/rdf-sparql-query/>`_ query language.

    .. versionadded:: 2.0
    """
    name = 'SPARQL'
    aliases = ['sparql']
    filenames = ['*.rq', '*.sparql']
    mimetypes = ['application/sparql-query']

    # character group definitions ::

    PN_CHARS_BASE_GRP = (u'a-zA-Z'
                         u'\u00c0-\u00d6'
                         u'\u00d8-\u00f6'
                         u'\u00f8-\u02ff'
                         u'\u0370-\u037d'
                         u'\u037f-\u1fff'
                         u'\u200c-\u200d'
                         u'\u2070-\u218f'
                         u'\u2c00-\u2fef'
                         u'\u3001-\ud7ff'
                         u'\uf900-\ufdcf'
                         u'\ufdf0-\ufffd')

    PN_CHARS_U_GRP = (PN_CHARS_BASE_GRP + '_')

    PN_CHARS_GRP = (PN_CHARS_U_GRP +
                    r'\-' +
                    r'0-9' +
                    u'\u00b7' +
                    u'\u0300-\u036f' +
                    u'\u203f-\u2040')

    HEX_GRP = '0-9A-Fa-f'

    PN_LOCAL_ESC_CHARS_GRP = r' _~.\-!$&"()*+,;=/?#@%'

    # terminal productions ::

    PN_CHARS_BASE = '[' + PN_CHARS_BASE_GRP + ']'

    PN_CHARS_U = '[' + PN_CHARS_U_GRP + ']'

    PN_CHARS = '[' + PN_CHARS_GRP + ']'

    HEX = '[' + HEX_GRP + ']'

    PN_LOCAL_ESC_CHARS = '[' + PN_LOCAL_ESC_CHARS_GRP + ']'

    IRIREF = r'<(?:[^<>"{}|^`\\\x00-\x20])*>'

    BLANK_NODE_LABEL = '_:[0-9' + PN_CHARS_U_GRP + '](?:[' + PN_CHARS_GRP + \
                       '.]*' + PN_CHARS + ')?'

    PN_PREFIX = PN_CHARS_BASE + '(?:[' + PN_CHARS_GRP + '.]*' + PN_CHARS + ')?'

    VARNAME = u'[0-9' + PN_CHARS_U_GRP + '][' + PN_CHARS_U_GRP + \
              u'0-9\u00b7\u0300-\u036f\u203f-\u2040]*'

    PERCENT = '%' + HEX + HEX

    PN_LOCAL_ESC = r'\\' + PN_LOCAL_ESC_CHARS

    PLX = '(?:' + PERCENT + ')|(?:' + PN_LOCAL_ESC + ')'

    PN_LOCAL = ('(?:[' + PN_CHARS_U_GRP + ':0-9' + ']|' + PLX + ')' +
                '(?:(?:[' + PN_CHARS_GRP + '.:]|' + PLX + ')*(?:[' +
                PN_CHARS_GRP + ':]|' + PLX + '))?')

    EXPONENT = r'[eE][+-]?\d+'

    # Lexer token definitions ::

    tokens = {
        'root': [
            (r'\s+', Text),
            # keywords ::
            (r'(?i)(select|construct|describe|ask|where|filter|group\s+by|minus|'
             r'distinct|reduced|from\s+named|from|order\s+by|desc|asc|limit|'
             r'offset|bindings|load|clear|drop|create|add|move|copy|'
             r'insert\s+data|delete\s+data|delete\s+where|delete|insert|'
             r'using\s+named|using|graph|default|named|all|optional|service|'
             r'silent|bind|union|not\s+in|in|as|having|to|prefix|base)\b', Keyword),
            (r'(a)\b', Keyword),
            # IRIs ::
            ('(' + IRIREF + ')', Name.Label),
            # blank nodes ::
            ('(' + BLANK_NODE_LABEL + ')', Name.Label),
            #  # variables ::
            ('[?$]' + VARNAME, Name.Variable),
            # prefixed names ::
            (r'(' + PN_PREFIX + r')?(\:)(' + PN_LOCAL + r')?',
             bygroups(Name.Namespace, Punctuation, Name.Tag)),
            # function names ::
            (r'(?i)(str|lang|langmatches|datatype|bound|iri|uri|bnode|rand|abs|'
             r'ceil|floor|round|concat|strlen|ucase|lcase|encode_for_uri|'
             r'contains|strstarts|strends|strbefore|strafter|year|month|day|'
             r'hours|minutes|seconds|timezone|tz|now|md5|sha1|sha256|sha384|'
             r'sha512|coalesce|if|strlang|strdt|sameterm|isiri|isuri|isblank|'
             r'isliteral|isnumeric|regex|substr|replace|exists|not\s+exists|'
             r'count|sum|min|max|avg|sample|group_concat|separator)\b',
             Name.Function),
            # boolean literals ::
            (r'(true|false)', Keyword.Constant),
            # double literals ::
            (r'[+\-]?(\d+\.\d*' + EXPONENT + r'|\.?\d+' + EXPONENT + ')', Number.Float),
            # decimal literals ::
            (r'[+\-]?(\d+\.\d*|\.\d+)', Number.Float),
            # integer literals ::
            (r'[+\-]?\d+', Number.Integer),
            # operators ::
            (r'(\|\||&&|=|\*|\-|\+|/|!=|<=|>=|!|<|>)', Operator),
            # punctuation characters ::
            (r'[(){}.;,:^\[\]]', Punctuation),
            # line comments ::
            (r'#[^\n]*', Comment),
            # strings ::
            (r'"""', String, 'triple-double-quoted-string'),
            (r'"', String, 'single-double-quoted-string'),
            (r"'''", String, 'triple-single-quoted-string'),
            (r"'", String, 'single-single-quoted-string'),
        ],
        'triple-double-quoted-string': [
            (r'"""', String, 'end-of-string'),
            (r'[^\\]+', String),
            (r'\\', String, 'string-escape'),
        ],
        'single-double-quoted-string': [
            (r'"', String, 'end-of-string'),
            (r'[^"\\\n]+', String),
            (r'\\', String, 'string-escape'),
        ],
        'triple-single-quoted-string': [
            (r"'''", String, 'end-of-string'),
            (r'[^\\]+', String),
            (r'\\', String.Escape, 'string-escape'),
        ],
        'single-single-quoted-string': [
            (r"'", String, 'end-of-string'),
            (r"[^'\\\n]+", String),
            (r'\\', String, 'string-escape'),
        ],
        'string-escape': [
            (r'u' + HEX + '{4}', String.Escape, '#pop'),
            (r'U' + HEX + '{8}', String.Escape, '#pop'),
            (r'.', String.Escape, '#pop'),
        ],
        'end-of-string': [
            (r'(@)([a-zA-Z]+(?:-[a-zA-Z0-9]+)*)',
             bygroups(Operator, Name.Function), '#pop:2'),
            (r'\^\^', Operator, '#pop:2'),
            default('#pop:2'),
        ],
    }


class TurtleLexer(RegexLexer):
    """
    Lexer for `Turtle <http://www.w3.org/TR/turtle/>`_ data language.

    .. versionadded:: 2.1
    """
    name = 'Turtle'
    aliases = ['turtle']
    filenames = ['*.ttl']
    mimetypes = ['text/turtle', 'application/x-turtle']

    flags = re.IGNORECASE

    patterns = {
        'PNAME_NS': r'((?:[a-z][\w-]*)?\:)',  # Simplified character range
        'IRIREF': r'(<[^<>"{}|^`\\\x00-\x20]*>)'
    }

    # PNAME_NS PN_LOCAL (with simplified character range)
    patterns['PrefixedName'] = r'%(PNAME_NS)s([a-z][\w-]*)' % patterns

    tokens = {
        'root': [
            (r'\s+', Whitespace),

            # Base / prefix
            (r'(@base|BASE)(\s+)%(IRIREF)s(\s*)(\.?)' % patterns,
             bygroups(Keyword, Whitespace, Name.Variable, Whitespace,
                      Punctuation)),
            (r'(@prefix|PREFIX)(\s+)%(PNAME_NS)s(\s+)%(IRIREF)s(\s*)(\.?)' % patterns,
             bygroups(Keyword, Whitespace, Name.Namespace, Whitespace,
                      Name.Variable, Whitespace, Punctuation)),

            # The shorthand predicate 'a'
            (r'(?<=\s)a(?=\s)', Keyword.Type),

            # IRIREF
            (r'%(IRIREF)s' % patterns, Name.Variable),

            # PrefixedName
            (r'%(PrefixedName)s' % patterns,
             bygroups(Name.Namespace, Name.Tag)),

            # Comment
            (r'#[^\n]+', Comment),

            (r'\b(true|false)\b', Literal),
            (r'[+\-]?\d*\.\d+', Number.Float),
            (r'[+\-]?\d*(:?\.\d+)?E[+\-]?\d+', Number.Float),
            (r'[+\-]?\d+', Number.Integer),
            (r'[\[\](){}.;,:^]', Punctuation),

            (r'"""', String, 'triple-double-quoted-string'),
            (r'"', String, 'single-double-quoted-string'),
            (r"'''", String, 'triple-single-quoted-string'),
            (r"'", String, 'single-single-quoted-string'),
        ],
        'triple-double-quoted-string': [
            (r'"""', String, 'end-of-string'),
            (r'[^\\]+', String),
            (r'\\', String, 'string-escape'),
        ],
        'single-double-quoted-string': [
            (r'"', String, 'end-of-string'),
            (r'[^"\\\n]+', String),
            (r'\\', String, 'string-escape'),
        ],
        'triple-single-quoted-string': [
            (r"'''", String, 'end-of-string'),
            (r'[^\\]+', String),
            (r'\\', String, 'string-escape'),
        ],
        'single-single-quoted-string': [
            (r"'", String, 'end-of-string'),
            (r"[^'\\\n]+", String),
            (r'\\', String, 'string-escape'),
        ],
        'string-escape': [
            (r'.', String, '#pop'),
        ],
        'end-of-string': [
            (r'(@)([a-z]+(:?-[a-z0-9]+)*)',
             bygroups(Operator, Generic.Emph), '#pop:2'),

            (r'(\^\^)%(IRIREF)s' % patterns, bygroups(Operator, Generic.Emph), '#pop:2'),
            (r'(\^\^)%(PrefixedName)s' % patterns,
             bygroups(Operator, Generic.Emph, Generic.Emph), '#pop:2'),

            default('#pop:2'),

        ],
    }
