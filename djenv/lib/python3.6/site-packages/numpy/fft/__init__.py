from __future__ import division, absolute_import, print_function

# To get sub-modules
from .info import __doc__

from .fftpack import *
from .helper import *

from numpy._pytesttester import PytestTester
test = PytestTester(__name__)
del PytestTester
