# -*- coding: utf-8 -*-
"""
    pygments.lexers.math
    ~~~~~~~~~~~~~~~~~~~~

    Just export lexers that were contained in this module.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexers.python import NumPyLexer
from pygments.lexers.matlab import MatlabLexer, MatlabSessionLexer, \
    OctaveLexer, ScilabLexer
from pygments.lexers.julia import JuliaLexer, JuliaConsoleLexer
from pygments.lexers.r import RConsoleLexer, SLexer, RdLexer
from pygments.lexers.modeling import BugsLexer, JagsLexer, StanLexer
from pygments.lexers.idl import IDLLexer
from pygments.lexers.algebra import MuPADLexer

__all__ = []
