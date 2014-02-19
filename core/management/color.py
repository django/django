"""
Sets up the terminal color scheme.
"""

import os
import sys

from django.utils import termcolors


def supports_color():
    """
    Returns True if the running system's terminal supports color, and False
    otherwise.
    """
    plat = sys.platform
    supported_platform = plat != 'Pocket PC' and (plat != 'win32' or
                                                  'ANSICON' in os.environ)
    # isatty is not always implemented, #6223.
    is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    if not supported_platform or not is_a_tty:
        return False
    return True


def color_style():
    """Returns a Style object with the Django color scheme."""
    if not supports_color():
        style = no_style()
    else:
        DJANGO_COLORS = os.environ.get('DJANGO_COLORS', '')
        color_settings = termcolors.parse_color_setting(DJANGO_COLORS)
        if color_settings:
            class dummy:
                pass
            style = dummy()
            # The nocolor palette has all available roles.
            # Use that palette as the basis for populating
            # the palette as defined in the environment.
            for role in termcolors.PALETTES[termcolors.NOCOLOR_PALETTE]:
                format = color_settings.get(role, {})
                setattr(style, role, termcolors.make_style(**format))
            # For backwards compatibility,
            # set style for ERROR_OUTPUT == ERROR
            style.ERROR_OUTPUT = style.ERROR
        else:
            style = no_style()
    return style


def no_style():
    """Returns a Style object that has no colors."""
    class dummy:
        def __getattr__(self, attr):
            return lambda x: x
    return dummy()
