# -*- coding: utf-8 -*-
"""
    pygments.lexers.graph
    ~~~~~~~~~~~~~~~~~~~~~

    Lexers for graph query languages.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, using, this
from pygments.token import Keyword, Punctuation, Comment, Operator, Name,\
    String, Number, Whitespace


__all__ = ['CypherLexer']


class CypherLexer(RegexLexer):
    """
    For `Cypher Query Language
    <http://docs.neo4j.org/chunked/milestone/cypher-query-lang.html>`_

    For the Cypher version in Neo4J 2.0

    .. versionadded:: 2.0
    """
    name = 'Cypher'
    aliases = ['cypher']
    filenames = ['*.cyp', '*.cypher']

    flags = re.MULTILINE | re.IGNORECASE

    tokens = {
        'root': [
            include('comment'),
            include('keywords'),
            include('clauses'),
            include('relations'),
            include('strings'),
            include('whitespace'),
            include('barewords'),
        ],
        'comment': [
            (r'^.*//.*\n', Comment.Single),
        ],
        'keywords': [
            (r'(create|order|match|limit|set|skip|start|return|with|where|'
             r'delete|foreach|not|by)\b', Keyword),
        ],
        'clauses': [
            # TODO: many missing ones, see http://docs.neo4j.org/refcard/2.0/
            (r'(all|any|as|asc|create|create\s+unique|delete|'
             r'desc|distinct|foreach|in|is\s+null|limit|match|none|'
             r'order\s+by|return|set|skip|single|start|union|where|with)\b',
             Keyword),
        ],
        'relations': [
            (r'(-\[)(.*?)(\]->)', bygroups(Operator, using(this), Operator)),
            (r'(<-\[)(.*?)(\]-)', bygroups(Operator, using(this), Operator)),
            (r'(-\[)(.*?)(\]-)', bygroups(Operator, using(this), Operator)),
            (r'-->|<--|\[|\]', Operator),
            (r'<|>|<>|=|<=|=>|\(|\)|\||:|,|;', Punctuation),
            (r'[.*{}]', Punctuation),
        ],
        'strings': [
            (r'"(?:\\[tbnrf\'"\\]|[^\\"])*"', String),
            (r'`(?:``|[^`])+`', Name.Variable),
        ],
        'whitespace': [
            (r'\s+', Whitespace),
        ],
        'barewords': [
            (r'[a-z]\w*', Name),
            (r'\d+', Number),
        ],
    }
