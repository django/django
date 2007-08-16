"""
Sets up the terminal color scheme.
"""

from django.utils import termcolors
import sys

def color_style():
    "Returns a Style object with the Django color scheme."
    if sys.platform == 'win32' or sys.platform == 'Pocket PC' or not sys.stdout.isatty():
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
    "Returns a Style object that has no colors."
    class dummy:
        def __getattr__(self, attr):
            return lambda x: x
    return dummy()
