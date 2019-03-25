"""Small modules to cope with python 2 vs 3 incompatibilities inside
numpy.distutils

"""
from __future__ import division, absolute_import, print_function

import sys

def get_exception():
    return sys.exc_info()[1]
