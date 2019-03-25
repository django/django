# -*- coding: utf-8 -*-
"""
    pygments.lexers.ezhil
    ~~~~~~~~~~~~~~~~~~~~~

    Pygments lexers for Ezhil language.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
from pygments.lexer import RegexLexer, include, words
from pygments.token import Keyword, Text, Comment, Name
from pygments.token import String, Number, Punctuation, Operator

__all__ = ['EzhilLexer']


class EzhilLexer(RegexLexer):
    """
    Lexer for `Ezhil, a Tamil script-based programming language <http://ezhillang.org>`_

    .. versionadded:: 2.1
    """
    name = 'Ezhil'
    aliases = ['ezhil']
    filenames = ['*.n']
    mimetypes = ['text/x-ezhil']
    flags = re.MULTILINE | re.UNICODE
    # Refer to tamil.utf8.tamil_letters from open-tamil for a stricter version of this.
    # This much simpler version is close enough, and includes combining marks.
    _TALETTERS = u'[a-zA-Z_]|[\u0b80-\u0bff]'
    tokens = {
        'root': [
            include('keywords'),
            (r'#.*\n', Comment.Single),
            (r'[@+/*,^\-%]|[!<>=]=?|&&?|\|\|?', Operator),
            (u'இல்', Operator.Word),
            (words((u'assert', u'max', u'min',
                    u'நீளம்', u'சரம்_இடமாற்று', u'சரம்_கண்டுபிடி',
                    u'பட்டியல்', u'பின்இணை', u'வரிசைப்படுத்து',
                    u'எடு', u'தலைகீழ்', u'நீட்டிக்க', u'நுழைக்க', u'வை',
                    u'கோப்பை_திற', u'கோப்பை_எழுது', u'கோப்பை_மூடு',
                    u'pi', u'sin', u'cos', u'tan', u'sqrt', u'hypot', u'pow',
                    u'exp', u'log', u'log10', u'exit',
                    ), suffix=r'\b'), Name.Builtin),
            (r'(True|False)\b', Keyword.Constant),
            (r'[^\S\n]+', Text),
            include('identifier'),
            include('literal'),
            (r'[(){}\[\]:;.]', Punctuation),
        ],
        'keywords': [
            (u'பதிப்பி|தேர்ந்தெடு|தேர்வு|ஏதேனில்|ஆனால்|இல்லைஆனால்|இல்லை|ஆக|ஒவ்வொன்றாக|இல்|வரை|செய்|முடியேனில்|பின்கொடு|முடி|நிரல்பாகம்|தொடர்|நிறுத்து|நிரல்பாகம்', Keyword),
        ],
        'identifier': [
            (u'(?:'+_TALETTERS+u')(?:[0-9]|'+_TALETTERS+u')*', Name),
        ],
        'literal': [
            (r'".*?"', String),
            (r'(?u)\d+((\.\d*)?[eE][+-]?\d+|\.\d*)', Number.Float),
            (r'(?u)\d+', Number.Integer),
        ]
    }

    def __init__(self, **options):
        super(EzhilLexer, self).__init__(**options)
        self.encoding = options.get('encoding', 'utf-8')
