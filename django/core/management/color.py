"""
Sets up the terminal color scheme.
"""

import sys

from django.utils import termcolors

def supports_color():
    """
    Returns True if the running system's terminal supports color, and False
    otherwise.
    """
    unsupported_platform = (sys.platform in ('win32', 'Pocket PC')
                            or sys.platform.startswith('java'))
    # isatty is not always implemented, #6223.
    is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    if unsupported_platform or not is_a_tty:
        return False
    return True

def color_style():
    """Returns a Style object with the Django color scheme."""
    if not supports_color():
        return no_style()
    class dummy: pass
    style = dummy()
    style.ERROR = termcolors.make_style(fg='red', opts=('bold',))
    style.ERROR_OUTPUT = termcolors.make_style(fg='red', opts=('bold',))
    style.NOTICE = termcolors.make_style(fg='red')
    style.SQL_FIELD = termcolors.make_style(fg='green', opts=('bold',))
    style.SQL_COLTYPE = termcolors.make_style(fg='green')
    style.SQL_KEYWORD = termcolors.make_style(fg='yellow')
    style.SQL_TABLE = termcolors.make_style(opts=('bold',))
    return style

def no_style():
    """Returns a Style object that has no colors."""
    class dummy:
        def __getattr__(self, attr):
            return lambda x: x
    return dummy()
