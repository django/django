#
# The Python Imaging Library
# $Id$
#
# simple postscript graphics interface
#
# History:
# 1996-04-20 fl   Created
# 1999-01-10 fl   Added gsave/grestore to image method
# 2005-05-04 fl   Fixed floating point issue in image (from Eric Etheridge)
#
# Copyright (c) 1997-2005 by Secret Labs AB.  All rights reserved.
# Copyright (c) 1996 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

from . import EpsImagePlugin
from ._util import py3
import sys

##
# Simple Postscript graphics interface.


class PSDraw(object):
    """
    Sets up printing to the given file. If **fp** is omitted,
    :py:attr:`sys.stdout` is assumed.
    """

    def __init__(self, fp=None):
        if not fp:
            fp = sys.stdout
        self.fp = fp

    def _fp_write(self, to_write):
        if not py3 or self.fp == sys.stdout:
            self.fp.write(to_write)
        else:
            self.fp.write(bytes(to_write, 'UTF-8'))

    def begin_document(self, id=None):
        """Set up printing of a document. (Write Postscript DSC header.)"""
        # FIXME: incomplete
        self._fp_write("%!PS-Adobe-3.0\n"
                       "save\n"
                       "/showpage { } def\n"
                       "%%EndComments\n"
                       "%%BeginDocument\n")
        # self._fp_write(ERROR_PS)  # debugging!
        self._fp_write(EDROFF_PS)
        self._fp_write(VDI_PS)
        self._fp_write("%%EndProlog\n")
        self.isofont = {}

    def end_document(self):
        """Ends printing. (Write Postscript DSC footer.)"""
        self._fp_write("%%EndDocument\n"
                       "restore showpage\n"
                       "%%End\n")
        if hasattr(self.fp, "flush"):
            self.fp.flush()

    def setfont(self, font, size):
        """
        Selects which font to use.

        :param font: A Postscript font name
        :param size: Size in points.
        """
        if font not in self.isofont:
            # reencode font
            self._fp_write("/PSDraw-%s ISOLatin1Encoding /%s E\n" %
                           (font, font))
            self.isofont[font] = 1
        # rough
        self._fp_write("/F0 %d /PSDraw-%s F\n" % (size, font))

    def line(self, xy0, xy1):
        """
        Draws a line between the two points. Coordinates are given in
        Postscript point coordinates (72 points per inch, (0, 0) is the lower
        left corner of the page).
        """
        xy = xy0 + xy1
        self._fp_write("%d %d %d %d Vl\n" % xy)

    def rectangle(self, box):
        """
        Draws a rectangle.

        :param box: A 4-tuple of integers whose order and function is currently
                    undocumented.

                    Hint: the tuple is passed into this format string:

                    .. code-block:: python

                        %d %d M %d %d 0 Vr\n
        """
        self._fp_write("%d %d M %d %d 0 Vr\n" % box)

    def text(self, xy, text):
        """
        Draws text at the given position. You must use
        :py:meth:`~PIL.PSDraw.PSDraw.setfont` before calling this method.
        """
        text = "\\(".join(text.split("("))
        text = "\\)".join(text.split(")"))
        xy = xy + (text,)
        self._fp_write("%d %d M (%s) S\n" % xy)

    def image(self, box, im, dpi=None):
        """Draw a PIL image, centered in the given box."""
        # default resolution depends on mode
        if not dpi:
            if im.mode == "1":
                dpi = 200  # fax
            else:
                dpi = 100  # greyscale
        # image size (on paper)
        x = float(im.size[0] * 72) / dpi
        y = float(im.size[1] * 72) / dpi
        # max allowed size
        xmax = float(box[2] - box[0])
        ymax = float(box[3] - box[1])
        if x > xmax:
            y = y * xmax / x
            x = xmax
        if y > ymax:
            x = x * ymax / y
            y = ymax
        dx = (xmax - x) / 2 + box[0]
        dy = (ymax - y) / 2 + box[1]
        self._fp_write("gsave\n%f %f translate\n" % (dx, dy))
        if (x, y) != im.size:
            # EpsImagePlugin._save prints the image at (0,0,xsize,ysize)
            sx = x / im.size[0]
            sy = y / im.size[1]
            self._fp_write("%f %f scale\n" % (sx, sy))
        EpsImagePlugin._save(im, self.fp, None, 0)
        self._fp_write("\ngrestore\n")

# --------------------------------------------------------------------
# Postscript driver

#
# EDROFF.PS -- Postscript driver for Edroff 2
#
# History:
# 94-01-25 fl: created (edroff 2.04)
#
# Copyright (c) Fredrik Lundh 1994.
#


EDROFF_PS = """\
/S { show } bind def
/P { moveto show } bind def
/M { moveto } bind def
/X { 0 rmoveto } bind def
/Y { 0 exch rmoveto } bind def
/E {    findfont
        dup maxlength dict begin
        {
                1 index /FID ne { def } { pop pop } ifelse
        } forall
        /Encoding exch def
        dup /FontName exch def
        currentdict end definefont pop
} bind def
/F {    findfont exch scalefont dup setfont
        [ exch /setfont cvx ] cvx bind def
} bind def
"""

#
# VDI.PS -- Postscript driver for VDI meta commands
#
# History:
# 94-01-25 fl: created (edroff 2.04)
#
# Copyright (c) Fredrik Lundh 1994.
#

VDI_PS = """\
/Vm { moveto } bind def
/Va { newpath arcn stroke } bind def
/Vl { moveto lineto stroke } bind def
/Vc { newpath 0 360 arc closepath } bind def
/Vr {   exch dup 0 rlineto
        exch dup neg 0 exch rlineto
        exch neg 0 rlineto
        0 exch rlineto
        100 div setgray fill 0 setgray } bind def
/Tm matrix def
/Ve {   Tm currentmatrix pop
        translate scale newpath 0 0 .5 0 360 arc closepath
        Tm setmatrix
} bind def
/Vf { currentgray exch setgray fill setgray } bind def
"""

#
# ERROR.PS -- Error handler
#
# History:
# 89-11-21 fl: created (pslist 1.10)
#

ERROR_PS = """\
/landscape false def
/errorBUF 200 string def
/errorNL { currentpoint 10 sub exch pop 72 exch moveto } def
errordict begin /handleerror {
    initmatrix /Courier findfont 10 scalefont setfont
    newpath 72 720 moveto $error begin /newerror false def
    (PostScript Error) show errorNL errorNL
    (Error: ) show
        /errorname load errorBUF cvs show errorNL errorNL
    (Command: ) show
        /command load dup type /stringtype ne { errorBUF cvs } if show
        errorNL errorNL
    (VMstatus: ) show
        vmstatus errorBUF cvs show ( bytes available, ) show
        errorBUF cvs show ( bytes used at level ) show
        errorBUF cvs show errorNL errorNL
    (Operand stargck: ) show errorNL /ostargck load {
        dup type /stringtype ne { errorBUF cvs } if 72 0 rmoveto show errorNL
    } forall errorNL
    (Execution stargck: ) show errorNL /estargck load {
        dup type /stringtype ne { errorBUF cvs } if 72 0 rmoveto show errorNL
    } forall
    end showpage
} def end
"""
