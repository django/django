"""
    pygments.lexers.functional
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Just export lexer classes previously contained in this module.

    :copyright: Copyright 2006-2023 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexers.lisp import SchemeLexer, CommonLispLexer, RacketLexer, \
    NewLispLexer, ShenLexer
from pygments.lexers.haskell import HaskellLexer, LiterateHaskellLexer, \
    KokaLexer
from pygments.lexers.theorem import CoqLexer
from pygments.lexers.erlang import ErlangLexer, ErlangShellLexer, \
    ElixirConsoleLexer, ElixirLexer
from pygments.lexers.ml import SMLLexer, OcamlLexer, OpaLexer

__all__ = []
