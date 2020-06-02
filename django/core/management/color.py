"""
Sets up the terminal color scheme.
"""

import functools
import os
import sys

from django.utils import termcolors


def supports_color():
    """
    Return True if the running system's terminal supports color,
    and False otherwise.
    """
    supported_platform = sys.platform != 'win32' or 'ANSICON' in os.environ

    # isatty is not always implemented, #6223.
    is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    return supported_platform and is_a_tty


class Style:
    pass


def make_style(config_string=''):
    """
    Create a Style object from the given config_string.

    If config_string is empty django.utils.termcolors.DEFAULT_PALETTE is used.
    """

    style = Style()

    color_settings = termcolors.parse_color_setting(config_string)

    # The nocolor palette has all available roles.
    # Use that palette as the basis for populating
    # the palette as defined in the environment.
    for role in termcolors.PALETTES[termcolors.NOCOLOR_PALETTE]:
        if color_settings:
            format = color_settings.get(role, {})
            style_func = termcolors.make_style(**format)
        else:
            def style_func(x):
                return x
        setattr(style, role, style_func)

    # For backwards compatibility,
    # set style for ERROR_OUTPUT == ERROR
    style.ERROR_OUTPUT = style.ERROR

    return style


@functools.lru_cache(maxsize=None)
def no_style():
    """
    Return a Style object with no color scheme.
    """
    return make_style('nocolor')


def color_style(force_color=False):
    """
    Return a Style object from the Django color scheme.
    """
    if not force_color and not supports_color():
        return no_style()
    return make_style(os.environ.get('DJANGO_COLORS', ''))
