"""
Django main module. When the package is run with `python -m django` this module
is run, so there is no need to test the __name__ variable. It *will* be "__main__".
"""

import os.path
import sys

from django.utils.version import get_version
    
sys.exit("""Django version {}
Loaded from {}
Python {}""".format(get_version(), os.path.dirname( __file__) , sys.version))
