# -*- coding: utf-8 -*-
"""
    pygments.lexers.text
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for non-source code file types.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexers.configs import ApacheConfLexer, NginxConfLexer, \
    SquidConfLexer, LighttpdConfLexer, IniLexer, RegeditLexer, PropertiesLexer
from pygments.lexers.console import PyPyLogLexer
from pygments.lexers.textedit import VimLexer
from pygments.lexers.markup import BBCodeLexer, MoinWikiLexer, RstLexer, \
    TexLexer, GroffLexer
from pygments.lexers.installers import DebianControlLexer, SourcesListLexer
from pygments.lexers.make import MakefileLexer, BaseMakefileLexer, CMakeLexer
from pygments.lexers.haxe import HxmlLexer
from pygments.lexers.diff import DiffLexer, DarcsPatchLexer
from pygments.lexers.data import YamlLexer
from pygments.lexers.textfmts import IrcLogsLexer, GettextLexer, HttpLexer

__all__ = []
