# -*- coding: utf-8 -*-
"""
    pygments.lexers.xorg
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for Xorg configs.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, bygroups
from pygments.token import Comment, String, Name, Text

__all__ = ['XorgLexer']


class XorgLexer(RegexLexer):
    """Lexer for xorg.conf file."""
    name = 'Xorg'
    aliases = ['xorg.conf']
    filenames = ['xorg.conf']
    mimetypes = []

    tokens = {
        'root': [
            (r'\s+', Text),
            (r'#.*$', Comment),

            (r'((?:Sub)?Section)(\s+)("\w+")',
             bygroups(String.Escape, Text, String.Escape)),
            (r'(End(|Sub)Section)', String.Escape),

            (r'(\w+)(\s+)([^\n#]+)',
             bygroups(Name.Builtin, Text, Name.Constant)),
        ],
    }
