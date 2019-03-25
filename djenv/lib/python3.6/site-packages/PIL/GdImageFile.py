#
# The Python Imaging Library.
# $Id$
#
# GD file handling
#
# History:
# 1996-04-12 fl   Created
#
# Copyright (c) 1997 by Secret Labs AB.
# Copyright (c) 1996 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#


# NOTE: This format cannot be automatically recognized, so the
# class is not registered for use with Image.open().  To open a
# gd file, use the GdImageFile.open() function instead.

# THE GD FORMAT IS NOT DESIGNED FOR DATA INTERCHANGE.  This
# implementation is provided for convenience and demonstrational
# purposes only.


from . import ImageFile, ImagePalette
from ._binary import i8, i16be as i16, i32be as i32

__version__ = "0.1"


##
# Image plugin for the GD uncompressed format.  Note that this format
# is not supported by the standard <b>Image.open</b> function.  To use
# this plugin, you have to import the <b>GdImageFile</b> module and
# use the <b>GdImageFile.open</b> function.

class GdImageFile(ImageFile.ImageFile):

    format = "GD"
    format_description = "GD uncompressed images"

    def _open(self):

        # Header
        s = self.fp.read(1037)

        if not i16(s[:2]) in [65534, 65535]:
            raise SyntaxError("Not a valid GD 2.x .gd file")

        self.mode = "L"  # FIXME: "P"
        self._size = i16(s[2:4]), i16(s[4:6])

        trueColor = i8(s[6])
        trueColorOffset = 2 if trueColor else 0

        # transparency index
        tindex = i32(s[7+trueColorOffset:7+trueColorOffset+4])
        if tindex < 256:
            self.info["transparency"] = tindex

        self.palette = ImagePalette.raw(
            "XBGR", s[7+trueColorOffset+4:7+trueColorOffset+4+256*4])

        self.tile = [("raw", (0, 0)+self.size, 7+trueColorOffset+4+256*4,
                      ("L", 0, 1))]


def open(fp, mode="r"):
    """
    Load texture from a GD image file.

    :param filename: GD file name, or an opened file handle.
    :param mode: Optional mode.  In this version, if the mode argument
        is given, it must be "r".
    :returns: An image instance.
    :raises IOError: If the image could not be read.
    """
    if mode != "r":
        raise ValueError("bad mode")

    try:
        return GdImageFile(fp)
    except SyntaxError:
        raise IOError("cannot identify this image file")
