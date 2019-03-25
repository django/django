#
# The Python Imaging Library
# $Id$
#
# FITS stub adapter
#
# Copyright (c) 1998-2003 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from . import Image, ImageFile

_handler = None


def register_handler(handler):
    """
    Install application-specific FITS image handler.

    :param handler: Handler object.
    """
    global _handler
    _handler = handler

# --------------------------------------------------------------------
# Image adapter


def _accept(prefix):
    return prefix[:6] == b"SIMPLE"


class FITSStubImageFile(ImageFile.StubImageFile):

    format = "FITS"
    format_description = "FITS"

    def _open(self):

        offset = self.fp.tell()

        if not _accept(self.fp.read(6)):
            raise SyntaxError("Not a FITS file")

        # FIXME: add more sanity checks here; mandatory header items
        # include SIMPLE, BITPIX, NAXIS, etc.

        self.fp.seek(offset)

        # make something up
        self.mode = "F"
        self._size = 1, 1

        loader = self._load()
        if loader:
            loader.open(self)

    def _load(self):
        return _handler


def _save(im, fp, filename):
    if _handler is None or not hasattr("_handler", "save"):
        raise IOError("FITS save handler not installed")
    _handler.save(im, fp, filename)


# --------------------------------------------------------------------
# Registry

Image.register_open(FITSStubImageFile.format, FITSStubImageFile, _accept)
Image.register_save(FITSStubImageFile.format, _save)

Image.register_extensions(FITSStubImageFile.format, [".fit", ".fits"])
