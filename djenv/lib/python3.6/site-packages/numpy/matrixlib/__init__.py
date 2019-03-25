"""Sub-package containing the matrix class and related functions.

"""
from __future__ import division, absolute_import, print_function

from .defmatrix import *

__all__ = defmatrix.__all__

from numpy._pytesttester import PytestTester
test = PytestTester(__name__)
del PytestTester
