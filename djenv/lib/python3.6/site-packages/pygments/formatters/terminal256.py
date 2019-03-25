# -*- coding: utf-8 -*-
"""
    pygments.formatters.terminal256
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for 256-color terminal output with ANSI sequences.

    RGB-to-XTERM color conversion routines adapted from xterm256-conv
    tool (http://frexx.de/xterm-256-notes/data/xterm256-conv2.tar.bz2)
    by Wolfgang Frisch.

    Formatter version 1.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# TODO:
#  - Options to map style's bold/underline/italic/border attributes
#    to some ANSI attrbutes (something like 'italic=underline')
#  - An option to output "style RGB to xterm RGB/index" conversion table
#  - An option to indicate that we are running in "reverse background"
#    xterm. This means that default colors are white-on-black, not
#    black-on-while, so colors like "white background" need to be converted
#    to "white background, black foreground", etc...

import sys

from pygments.formatter import Formatter
from pygments.console import codes
from pygments.style import ansicolors


__all__ = ['Terminal256Formatter', 'TerminalTrueColorFormatter']


class EscapeSequence:
    def __init__(self, fg=None, bg=None, bold=False, underline=False):
        self.fg = fg
        self.bg = bg
        self.bold = bold
        self.underline = underline

    def escape(self, attrs):
        if len(attrs):
            return "\x1b[" + ";".join(attrs) + "m"
        return ""

    def color_string(self):
        attrs = []
        if self.fg is not None:
            if self.fg in ansicolors:
                esc = codes[self.fg[5:]]
                if ';01m' in esc:
                    self.bold = True
                # extract fg color code.
                attrs.append(esc[2:4])
            else:
                attrs.extend(("38", "5", "%i" % self.fg))
        if self.bg is not None:
            if self.bg in ansicolors:
                esc = codes[self.bg[5:]]
                # extract fg color code, add 10 for bg.
                attrs.append(str(int(esc[2:4])+10))
            else:
                attrs.extend(("48", "5", "%i" % self.bg))
        if self.bold:
            attrs.append("01")
        if self.underline:
            attrs.append("04")
        return self.escape(attrs)

    def true_color_string(self):
        attrs = []
        if self.fg:
            attrs.extend(("38", "2", str(self.fg[0]), str(self.fg[1]), str(self.fg[2])))
        if self.bg:
            attrs.extend(("48", "2", str(self.bg[0]), str(self.bg[1]), str(self.bg[2])))
        if self.bold:
            attrs.append("01")
        if self.underline:
            attrs.append("04")
        return self.escape(attrs)

    def reset_string(self):
        attrs = []
        if self.fg is not None:
            attrs.append("39")
        if self.bg is not None:
            attrs.append("49")
        if self.bold or self.underline:
            attrs.append("00")
        return self.escape(attrs)


class Terminal256Formatter(Formatter):
    """
    Format tokens with ANSI color sequences, for output in a 256-color
    terminal or console.  Like in `TerminalFormatter` color sequences
    are terminated at newlines, so that paging the output works correctly.

    The formatter takes colors from a style defined by the `style` option
    and converts them to nearest ANSI 256-color escape sequences. Bold and
    underline attributes from the style are preserved (and displayed).

    .. versionadded:: 0.9

    .. versionchanged:: 2.2
       If the used style defines foreground colors in the form ``#ansi*``, then
       `Terminal256Formatter` will map these to non extended foreground color.
       See :ref:`AnsiTerminalStyle` for more information.

    Options accepted:

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).
    """
    name = 'Terminal256'
    aliases = ['terminal256', 'console256', '256']
    filenames = []

    def __init__(self, **options):
        Formatter.__init__(self, **options)

        self.xterm_colors = []
        self.best_match = {}
        self.style_string = {}

        self.usebold = 'nobold' not in options
        self.useunderline = 'nounderline' not in options

        self._build_color_table()  # build an RGB-to-256 color conversion table
        self._setup_styles()  # convert selected style's colors to term. colors

    def _build_color_table(self):
        # colors 0..15: 16 basic colors

        self.xterm_colors.append((0x00, 0x00, 0x00))  # 0
        self.xterm_colors.append((0xcd, 0x00, 0x00))  # 1
        self.xterm_colors.append((0x00, 0xcd, 0x00))  # 2
        self.xterm_colors.append((0xcd, 0xcd, 0x00))  # 3
        self.xterm_colors.append((0x00, 0x00, 0xee))  # 4
        self.xterm_colors.append((0xcd, 0x00, 0xcd))  # 5
        self.xterm_colors.append((0x00, 0xcd, 0xcd))  # 6
        self.xterm_colors.append((0xe5, 0xe5, 0xe5))  # 7
        self.xterm_colors.append((0x7f, 0x7f, 0x7f))  # 8
        self.xterm_colors.append((0xff, 0x00, 0x00))  # 9
        self.xterm_colors.append((0x00, 0xff, 0x00))  # 10
        self.xterm_colors.append((0xff, 0xff, 0x00))  # 11
        self.xterm_colors.append((0x5c, 0x5c, 0xff))  # 12
        self.xterm_colors.append((0xff, 0x00, 0xff))  # 13
        self.xterm_colors.append((0x00, 0xff, 0xff))  # 14
        self.xterm_colors.append((0xff, 0xff, 0xff))  # 15

        # colors 16..232: the 6x6x6 color cube

        valuerange = (0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff)

        for i in range(217):
            r = valuerange[(i // 36) % 6]
            g = valuerange[(i // 6) % 6]
            b = valuerange[i % 6]
            self.xterm_colors.append((r, g, b))

        # colors 233..253: grayscale

        for i in range(1, 22):
            v = 8 + i * 10
            self.xterm_colors.append((v, v, v))

    def _closest_color(self, r, g, b):
        distance = 257*257*3  # "infinity" (>distance from #000000 to #ffffff)
        match = 0

        for i in range(0, 254):
            values = self.xterm_colors[i]

            rd = r - values[0]
            gd = g - values[1]
            bd = b - values[2]
            d = rd*rd + gd*gd + bd*bd

            if d < distance:
                match = i
                distance = d
        return match

    def _color_index(self, color):
        index = self.best_match.get(color, None)
        if color in ansicolors:
            # strip the `#ansi` part and look up code
            index = color
            self.best_match[color] = index
        if index is None:
            try:
                rgb = int(str(color), 16)
            except ValueError:
                rgb = 0

            r = (rgb >> 16) & 0xff
            g = (rgb >> 8) & 0xff
            b = rgb & 0xff
            index = self._closest_color(r, g, b)
            self.best_match[color] = index
        return index

    def _setup_styles(self):
        for ttype, ndef in self.style:
            escape = EscapeSequence()
            # get foreground from ansicolor if set
            if ndef['ansicolor']:
                escape.fg = self._color_index(ndef['ansicolor'])
            elif ndef['color']:
                escape.fg = self._color_index(ndef['color'])
            if ndef['bgansicolor']:
                escape.bg = self._color_index(ndef['bgansicolor'])
            elif ndef['bgcolor']:
                escape.bg = self._color_index(ndef['bgcolor'])
            if self.usebold and ndef['bold']:
                escape.bold = True
            if self.useunderline and ndef['underline']:
                escape.underline = True
            self.style_string[str(ttype)] = (escape.color_string(),
                                             escape.reset_string())

    def format(self, tokensource, outfile):
        # hack: if the output is a terminal and has an encoding set,
        # use that to avoid unicode encode problems
        if not self.encoding and hasattr(outfile, "encoding") and \
           hasattr(outfile, "isatty") and outfile.isatty() and \
           sys.version_info < (3,):
            self.encoding = outfile.encoding
        return Formatter.format(self, tokensource, outfile)

    def format_unencoded(self, tokensource, outfile):
        for ttype, value in tokensource:
            not_found = True
            while ttype and not_found:
                try:
                    # outfile.write( "<" + str(ttype) + ">" )
                    on, off = self.style_string[str(ttype)]

                    # Like TerminalFormatter, add "reset colors" escape sequence
                    # on newline.
                    spl = value.split('\n')
                    for line in spl[:-1]:
                        if line:
                            outfile.write(on + line + off)
                        outfile.write('\n')
                    if spl[-1]:
                        outfile.write(on + spl[-1] + off)

                    not_found = False
                    # outfile.write( '#' + str(ttype) + '#' )

                except KeyError:
                    # ottype = ttype
                    ttype = ttype[:-1]
                    # outfile.write( '!' + str(ottype) + '->' + str(ttype) + '!' )

            if not_found:
                outfile.write(value)


class TerminalTrueColorFormatter(Terminal256Formatter):
    r"""
    Format tokens with ANSI color sequences, for output in a true-color
    terminal or console.  Like in `TerminalFormatter` color sequences
    are terminated at newlines, so that paging the output works correctly.

    .. versionadded:: 2.1

    Options accepted:

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).
    """
    name = 'TerminalTrueColor'
    aliases = ['terminal16m', 'console16m', '16m']
    filenames = []

    def _build_color_table(self):
        pass

    def _color_tuple(self, color):
        try:
            rgb = int(str(color), 16)
        except ValueError:
            return None
        r = (rgb >> 16) & 0xff
        g = (rgb >> 8) & 0xff
        b = rgb & 0xff
        return (r, g, b)

    def _setup_styles(self):
        for ttype, ndef in self.style:
            escape = EscapeSequence()
            if ndef['color']:
                escape.fg = self._color_tuple(ndef['color'])
            if ndef['bgcolor']:
                escape.bg = self._color_tuple(ndef['bgcolor'])
            if self.usebold and ndef['bold']:
                escape.bold = True
            if self.useunderline and ndef['underline']:
                escape.underline = True
            self.style_string[str(ttype)] = (escape.true_color_string(),
                                             escape.reset_string())
