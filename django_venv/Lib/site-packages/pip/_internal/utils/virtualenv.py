import os.path
import site
import sys


def running_under_virtualenv():
    # type: () -> bool
    """
    Return True if we're running inside a virtualenv, False otherwise.

    """
    if hasattr(sys, 'real_prefix'):
        # pypa/virtualenv case
        return True
    elif sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        # PEP 405 venv
        return True

    return False


def virtualenv_no_global():
    # type: () -> bool
    """
    Return True if in a venv and no system site packages.
    """
    # this mirrors the logic in virtualenv.py for locating the
    # no-global-site-packages.txt file
    site_mod_dir = os.path.dirname(os.path.abspath(site.__file__))
    no_global_file = os.path.join(site_mod_dir, 'no-global-site-packages.txt')
    if running_under_virtualenv() and os.path.isfile(no_global_file):
        return True
    else:
        return False
