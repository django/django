#
# The Python Imaging Library.
# $Id$
#
# the Image class wrapper
#
# partial release history:
# 1995-09-09 fl   Created
# 1996-03-11 fl   PIL release 0.0 (proof of concept)
# 1996-04-30 fl   PIL release 0.1b1
# 1999-07-28 fl   PIL release 1.0 final
# 2000-06-07 fl   PIL release 1.1
# 2000-10-20 fl   PIL release 1.1.1
# 2001-05-07 fl   PIL release 1.1.2
# 2002-03-15 fl   PIL release 1.1.3
# 2003-05-10 fl   PIL release 1.1.4
# 2005-03-28 fl   PIL release 1.1.5
# 2006-12-02 fl   PIL release 1.1.6
# 2009-11-15 fl   PIL release 1.1.7
#
# Copyright (c) 1997-2009 by Secret Labs AB.  All rights reserved.
# Copyright (c) 1995-2009 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

# VERSION is deprecated and will be removed in Pillow 6.0.0.
# PILLOW_VERSION is deprecated and will be removed after that.
# Use __version__ instead.
from . import VERSION, PILLOW_VERSION, __version__, _plugins
from ._util import py3

import logging
import warnings
import math

try:
    import builtins
except ImportError:
    import __builtin__
    builtins = __builtin__

from . import ImageMode
from ._binary import i8
from ._util import isPath, isStringType, deferred_error

import os
import sys
import io
import struct
import atexit

# type stuff
import numbers
try:
    # Python 3
    from collections.abc import Callable
except ImportError:
    # Python 2.7
    from collections import Callable


# Silence warnings
assert VERSION
assert PILLOW_VERSION

logger = logging.getLogger(__name__)


class DecompressionBombWarning(RuntimeWarning):
    pass


class DecompressionBombError(Exception):
    pass


class _imaging_not_installed(object):
    # module placeholder
    def __getattr__(self, id):
        raise ImportError("The _imaging C module is not installed")


# Limit to around a quarter gigabyte for a 24 bit (3 bpp) image
MAX_IMAGE_PIXELS = int(1024 * 1024 * 1024 // 4 // 3)


try:
    # If the _imaging C module is not present, Pillow will not load.
    # Note that other modules should not refer to _imaging directly;
    # import Image and use the Image.core variable instead.
    # Also note that Image.core is not a publicly documented interface,
    # and should be considered private and subject to change.
    from . import _imaging as core
    if __version__ != getattr(core, 'PILLOW_VERSION', None):
        raise ImportError("The _imaging extension was built for another "
                          "version of Pillow or PIL:\n"
                          "Core version: %s\n"
                          "Pillow version: %s" %
                          (getattr(core, 'PILLOW_VERSION', None),
                           __version__))

except ImportError as v:
    core = _imaging_not_installed()
    # Explanations for ways that we know we might have an import error
    if str(v).startswith("Module use of python"):
        # The _imaging C module is present, but not compiled for
        # the right version (windows only).  Print a warning, if
        # possible.
        warnings.warn(
            "The _imaging extension was built for another version "
            "of Python.",
            RuntimeWarning
            )
    elif str(v).startswith("The _imaging extension"):
        warnings.warn(str(v), RuntimeWarning)
    elif "Symbol not found: _PyUnicodeUCS2_" in str(v):
        # should match _PyUnicodeUCS2_FromString and
        # _PyUnicodeUCS2_AsLatin1String
        warnings.warn(
            "The _imaging extension was built for Python with UCS2 support; "
            "recompile Pillow or build Python --without-wide-unicode. ",
            RuntimeWarning
            )
    elif "Symbol not found: _PyUnicodeUCS4_" in str(v):
        # should match _PyUnicodeUCS4_FromString and
        # _PyUnicodeUCS4_AsLatin1String
        warnings.warn(
            "The _imaging extension was built for Python with UCS4 support; "
            "recompile Pillow or build Python --with-wide-unicode. ",
            RuntimeWarning
            )
    # Fail here anyway. Don't let people run with a mostly broken Pillow.
    # see docs/porting.rst
    raise


# works everywhere, win for pypy, not cpython
USE_CFFI_ACCESS = hasattr(sys, 'pypy_version_info')
try:
    import cffi
except ImportError:
    cffi = None

try:
    from pathlib import Path
    HAS_PATHLIB = True
except ImportError:
    try:
        from pathlib2 import Path
        HAS_PATHLIB = True
    except ImportError:
        HAS_PATHLIB = False


def isImageType(t):
    """
    Checks if an object is an image object.

    .. warning::

       This function is for internal use only.

    :param t: object to check if it's an image
    :returns: True if the object is an image
    """
    return hasattr(t, "im")


#
# Constants

NONE = 0

# transpose
FLIP_LEFT_RIGHT = 0
FLIP_TOP_BOTTOM = 1
ROTATE_90 = 2
ROTATE_180 = 3
ROTATE_270 = 4
TRANSPOSE = 5
TRANSVERSE = 6

# transforms (also defined in Imaging.h)
AFFINE = 0
EXTENT = 1
PERSPECTIVE = 2
QUAD = 3
MESH = 4

# resampling filters (also defined in Imaging.h)
NEAREST = NONE = 0
BOX = 4
BILINEAR = LINEAR = 2
HAMMING = 5
BICUBIC = CUBIC = 3
LANCZOS = ANTIALIAS = 1

# dithers
NEAREST = NONE = 0
ORDERED = 1  # Not yet implemented
RASTERIZE = 2  # Not yet implemented
FLOYDSTEINBERG = 3  # default

# palettes/quantizers
WEB = 0
ADAPTIVE = 1

MEDIANCUT = 0
MAXCOVERAGE = 1
FASTOCTREE = 2
LIBIMAGEQUANT = 3

# categories
NORMAL = 0
SEQUENCE = 1
CONTAINER = 2

if hasattr(core, 'DEFAULT_STRATEGY'):
    DEFAULT_STRATEGY = core.DEFAULT_STRATEGY
    FILTERED = core.FILTERED
    HUFFMAN_ONLY = core.HUFFMAN_ONLY
    RLE = core.RLE
    FIXED = core.FIXED


# --------------------------------------------------------------------
# Registries

ID = []
OPEN = {}
MIME = {}
SAVE = {}
SAVE_ALL = {}
EXTENSION = {}
DECODERS = {}
ENCODERS = {}

# --------------------------------------------------------------------
# Modes supported by this version

_MODEINFO = {
    # NOTE: this table will be removed in future versions.  use
    # getmode* functions or ImageMode descriptors instead.

    # official modes
    "1": ("L", "L", ("1",)),
    "L": ("L", "L", ("L",)),
    "I": ("L", "I", ("I",)),
    "F": ("L", "F", ("F",)),
    "P": ("RGB", "L", ("P",)),
    "RGB": ("RGB", "L", ("R", "G", "B")),
    "RGBX": ("RGB", "L", ("R", "G", "B", "X")),
    "RGBA": ("RGB", "L", ("R", "G", "B", "A")),
    "CMYK": ("RGB", "L", ("C", "M", "Y", "K")),
    "YCbCr": ("RGB", "L", ("Y", "Cb", "Cr")),
    "LAB": ("RGB", "L", ("L", "A", "B")),
    "HSV": ("RGB", "L", ("H", "S", "V")),

    # Experimental modes include I;16, I;16L, I;16B, RGBa, BGR;15, and
    # BGR;24.  Use these modes only if you know exactly what you're
    # doing...

}

if sys.byteorder == 'little':
    _ENDIAN = '<'
else:
    _ENDIAN = '>'

_MODE_CONV = {
    # official modes
    "1": ('|b1', None),  # Bits need to be extended to bytes
    "L": ('|u1', None),
    "LA": ('|u1', 2),
    "I": (_ENDIAN + 'i4', None),
    "F": (_ENDIAN + 'f4', None),
    "P": ('|u1', None),
    "RGB": ('|u1', 3),
    "RGBX": ('|u1', 4),
    "RGBA": ('|u1', 4),
    "CMYK": ('|u1', 4),
    "YCbCr": ('|u1', 3),
    "LAB": ('|u1', 3),  # UNDONE - unsigned |u1i1i1
    "HSV": ('|u1', 3),
    # I;16 == I;16L, and I;32 == I;32L
    "I;16": ('<u2', None),
    "I;16B": ('>u2', None),
    "I;16L": ('<u2', None),
    "I;16S": ('<i2', None),
    "I;16BS": ('>i2', None),
    "I;16LS": ('<i2', None),
    "I;32": ('<u4', None),
    "I;32B": ('>u4', None),
    "I;32L": ('<u4', None),
    "I;32S": ('<i4', None),
    "I;32BS": ('>i4', None),
    "I;32LS": ('<i4', None),
}


def _conv_type_shape(im):
    typ, extra = _MODE_CONV[im.mode]
    if extra is None:
        return (im.size[1], im.size[0]), typ
    else:
        return (im.size[1], im.size[0], extra), typ


MODES = sorted(_MODEINFO)

# raw modes that may be memory mapped.  NOTE: if you change this, you
# may have to modify the stride calculation in map.c too!
_MAPMODES = ("L", "P", "RGBX", "RGBA", "CMYK", "I;16", "I;16L", "I;16B")


def getmodebase(mode):
    """
    Gets the "base" mode for given mode.  This function returns "L" for
    images that contain grayscale data, and "RGB" for images that
    contain color data.

    :param mode: Input mode.
    :returns: "L" or "RGB".
    :exception KeyError: If the input mode was not a standard mode.
    """
    return ImageMode.getmode(mode).basemode


def getmodetype(mode):
    """
    Gets the storage type mode.  Given a mode, this function returns a
    single-layer mode suitable for storing individual bands.

    :param mode: Input mode.
    :returns: "L", "I", or "F".
    :exception KeyError: If the input mode was not a standard mode.
    """
    return ImageMode.getmode(mode).basetype


def getmodebandnames(mode):
    """
    Gets a list of individual band names.  Given a mode, this function returns
    a tuple containing the names of individual bands (use
    :py:method:`~PIL.Image.getmodetype` to get the mode used to store each
    individual band.

    :param mode: Input mode.
    :returns: A tuple containing band names.  The length of the tuple
        gives the number of bands in an image of the given mode.
    :exception KeyError: If the input mode was not a standard mode.
    """
    return ImageMode.getmode(mode).bands


def getmodebands(mode):
    """
    Gets the number of individual bands for this mode.

    :param mode: Input mode.
    :returns: The number of bands in this mode.
    :exception KeyError: If the input mode was not a standard mode.
    """
    return len(ImageMode.getmode(mode).bands)


# --------------------------------------------------------------------
# Helpers

_initialized = 0


def preinit():
    """Explicitly load standard file format drivers."""

    global _initialized
    if _initialized >= 1:
        return

    try:
        from . import BmpImagePlugin
        assert BmpImagePlugin
    except ImportError:
        pass
    try:
        from . import GifImagePlugin
        assert GifImagePlugin
    except ImportError:
        pass
    try:
        from . import JpegImagePlugin
        assert JpegImagePlugin
    except ImportError:
        pass
    try:
        from . import PpmImagePlugin
        assert PpmImagePlugin
    except ImportError:
        pass
    try:
        from . import PngImagePlugin
        assert PngImagePlugin
    except ImportError:
        pass
#   try:
#       import TiffImagePlugin
#       assert TiffImagePlugin
#   except ImportError:
#       pass

    _initialized = 1


def init():
    """
    Explicitly initializes the Python Imaging Library. This function
    loads all available file format drivers.
    """

    global _initialized
    if _initialized >= 2:
        return 0

    for plugin in _plugins:
        try:
            logger.debug("Importing %s", plugin)
            __import__("PIL.%s" % plugin, globals(), locals(), [])
        except ImportError as e:
            logger.debug("Image: failed to import %s: %s", plugin, e)

    if OPEN or SAVE:
        _initialized = 2
        return 1


# --------------------------------------------------------------------
# Codec factories (used by tobytes/frombytes and ImageFile.load)

def _getdecoder(mode, decoder_name, args, extra=()):

    # tweak arguments
    if args is None:
        args = ()
    elif not isinstance(args, tuple):
        args = (args,)

    try:
        decoder = DECODERS[decoder_name]
        return decoder(mode, *args + extra)
    except KeyError:
        pass
    try:
        # get decoder
        decoder = getattr(core, decoder_name + "_decoder")
        return decoder(mode, *args + extra)
    except AttributeError:
        raise IOError("decoder %s not available" % decoder_name)


def _getencoder(mode, encoder_name, args, extra=()):

    # tweak arguments
    if args is None:
        args = ()
    elif not isinstance(args, tuple):
        args = (args,)

    try:
        encoder = ENCODERS[encoder_name]
        return encoder(mode, *args + extra)
    except KeyError:
        pass
    try:
        # get encoder
        encoder = getattr(core, encoder_name + "_encoder")
        return encoder(mode, *args + extra)
    except AttributeError:
        raise IOError("encoder %s not available" % encoder_name)


# --------------------------------------------------------------------
# Simple expression analyzer

def coerce_e(value):
    return value if isinstance(value, _E) else _E(value)


class _E(object):
    def __init__(self, data):
        self.data = data

    def __add__(self, other):
        return _E((self.data, "__add__", coerce_e(other).data))

    def __mul__(self, other):
        return _E((self.data, "__mul__", coerce_e(other).data))


def _getscaleoffset(expr):
    stub = ["stub"]
    data = expr(_E(stub)).data
    try:
        (a, b, c) = data  # simplified syntax
        if (a is stub and b == "__mul__" and isinstance(c, numbers.Number)):
            return c, 0.0
        if a is stub and b == "__add__" and isinstance(c, numbers.Number):
            return 1.0, c
    except TypeError:
        pass
    try:
        ((a, b, c), d, e) = data  # full syntax
        if (a is stub and b == "__mul__" and isinstance(c, numbers.Number) and
                d == "__add__" and isinstance(e, numbers.Number)):
            return c, e
    except TypeError:
        pass
    raise ValueError("illegal expression")


# --------------------------------------------------------------------
# Implementation wrapper

class Image(object):
    """
    This class represents an image object.  To create
    :py:class:`~PIL.Image.Image` objects, use the appropriate factory
    functions.  There's hardly ever any reason to call the Image constructor
    directly.

    * :py:func:`~PIL.Image.open`
    * :py:func:`~PIL.Image.new`
    * :py:func:`~PIL.Image.frombytes`
    """
    format = None
    format_description = None
    _close_exclusive_fp_after_loading = True

    def __init__(self):
        # FIXME: take "new" parameters / other image?
        # FIXME: turn mode and size into delegating properties?
        self.im = None
        self.mode = ""
        self._size = (0, 0)
        self.palette = None
        self.info = {}
        self.category = NORMAL
        self.readonly = 0
        self.pyaccess = None

    @property
    def width(self):
        return self.size[0]

    @property
    def height(self):
        return self.size[1]

    @property
    def size(self):
        return self._size

    def _new(self, im):
        new = Image()
        new.im = im
        new.mode = im.mode
        new._size = im.size
        if im.mode in ('P', 'PA'):
            if self.palette:
                new.palette = self.palette.copy()
            else:
                from . import ImagePalette
                new.palette = ImagePalette.ImagePalette()
        new.info = self.info.copy()
        return new

    # Context manager support
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        """
        Closes the file pointer, if possible.

        This operation will destroy the image core and release its memory.
        The image data will be unusable afterward.

        This function is only required to close images that have not
        had their file read and closed by the
        :py:meth:`~PIL.Image.Image.load` method. See
        :ref:`file-handling` for more information.
        """
        try:
            if hasattr(self, "_close__fp"):
                self._close__fp()
            self.fp.close()
            self.fp = None
        except Exception as msg:
            logger.debug("Error closing: %s", msg)

        if getattr(self, 'map', None):
            self.map = None

        # Instead of simply setting to None, we're setting up a
        # deferred error that will better explain that the core image
        # object is gone.
        self.im = deferred_error(ValueError("Operation on closed image"))

    if sys.version_info.major >= 3:
        def __del__(self):
            if hasattr(self, "_close__fp"):
                self._close__fp()
            if (hasattr(self, 'fp') and hasattr(self, '_exclusive_fp')
               and self.fp and self._exclusive_fp):
                self.fp.close()
            self.fp = None

    def _copy(self):
        self.load()
        self.im = self.im.copy()
        self.pyaccess = None
        self.readonly = 0

    def _ensure_mutable(self):
        if self.readonly:
            self._copy()
        else:
            self.load()

    def _dump(self, file=None, format=None, **options):
        import tempfile

        suffix = ''
        if format:
            suffix = '.'+format

        if not file:
            f, filename = tempfile.mkstemp(suffix)
            os.close(f)
        else:
            filename = file
            if not filename.endswith(suffix):
                filename = filename + suffix

        self.load()

        if not format or format == "PPM":
            self.im.save_ppm(filename)
        else:
            self.save(filename, format, **options)

        return filename

    def __eq__(self, other):
        return (isinstance(other, Image) and
                self.__class__.__name__ == other.__class__.__name__ and
                self.mode == other.mode and
                self.size == other.size and
                self.info == other.info and
                self.category == other.category and
                self.readonly == other.readonly and
                self.getpalette() == other.getpalette() and
                self.tobytes() == other.tobytes())

    def __ne__(self, other):
        eq = (self == other)
        return not eq

    def __repr__(self):
        return "<%s.%s image mode=%s size=%dx%d at 0x%X>" % (
            self.__class__.__module__, self.__class__.__name__,
            self.mode, self.size[0], self.size[1],
            id(self)
            )

    def _repr_png_(self):
        """ iPython display hook support

        :returns: png version of the image as bytes
        """
        from io import BytesIO
        b = BytesIO()
        self.save(b, 'PNG')
        return b.getvalue()

    @property
    def __array_interface__(self):
        # numpy array interface support
        new = {}
        shape, typestr = _conv_type_shape(self)
        new['shape'] = shape
        new['typestr'] = typestr
        new['version'] = 3
        if self.mode == '1':
            # Binary images need to be extended from bits to bytes
            # See: https://github.com/python-pillow/Pillow/issues/350
            new['data'] = self.tobytes('raw', 'L')
        else:
            new['data'] = self.tobytes()
        return new

    def __getstate__(self):
        return [
            self.info,
            self.mode,
            self.size,
            self.getpalette(),
            self.tobytes()]

    def __setstate__(self, state):
        Image.__init__(self)
        self.tile = []
        info, mode, size, palette, data = state
        self.info = info
        self.mode = mode
        self._size = size
        self.im = core.new(mode, size)
        if mode in ("L", "P") and palette:
            self.putpalette(palette)
        self.frombytes(data)

    def tobytes(self, encoder_name="raw", *args):
        """
        Return image as a bytes object.

        .. warning::

            This method returns the raw image data from the internal
            storage.  For compressed image data (e.g. PNG, JPEG) use
            :meth:`~.save`, with a BytesIO parameter for in-memory
            data.

        :param encoder_name: What encoder to use.  The default is to
                             use the standard "raw" encoder.
        :param args: Extra arguments to the encoder.
        :rtype: A bytes object.
        """

        # may pass tuple instead of argument list
        if len(args) == 1 and isinstance(args[0], tuple):
            args = args[0]

        if encoder_name == "raw" and args == ():
            args = self.mode

        self.load()

        # unpack data
        e = _getencoder(self.mode, encoder_name, args)
        e.setimage(self.im)

        bufsize = max(65536, self.size[0] * 4)  # see RawEncode.c

        data = []
        while True:
            l, s, d = e.encode(bufsize)
            data.append(d)
            if s:
                break
        if s < 0:
            raise RuntimeError("encoder error %d in tobytes" % s)

        return b"".join(data)

    def tostring(self, *args, **kw):
        raise NotImplementedError("tostring() has been removed. "
                                  "Please call tobytes() instead.")

    def tobitmap(self, name="image"):
        """
        Returns the image converted to an X11 bitmap.

        .. note:: This method only works for mode "1" images.

        :param name: The name prefix to use for the bitmap variables.
        :returns: A string containing an X11 bitmap.
        :raises ValueError: If the mode is not "1"
        """

        self.load()
        if self.mode != "1":
            raise ValueError("not a bitmap")
        data = self.tobytes("xbm")
        return b"".join([
            ("#define %s_width %d\n" % (name, self.size[0])).encode('ascii'),
            ("#define %s_height %d\n" % (name, self.size[1])).encode('ascii'),
            ("static char %s_bits[] = {\n" % name).encode('ascii'), data, b"};"
            ])

    def frombytes(self, data, decoder_name="raw", *args):
        """
        Loads this image with pixel data from a bytes object.

        This method is similar to the :py:func:`~PIL.Image.frombytes` function,
        but loads data into this image instead of creating a new image object.
        """

        # may pass tuple instead of argument list
        if len(args) == 1 and isinstance(args[0], tuple):
            args = args[0]

        # default format
        if decoder_name == "raw" and args == ():
            args = self.mode

        # unpack data
        d = _getdecoder(self.mode, decoder_name, args)
        d.setimage(self.im)
        s = d.decode(data)

        if s[0] >= 0:
            raise ValueError("not enough image data")
        if s[1] != 0:
            raise ValueError("cannot decode image data")

    def fromstring(self, *args, **kw):
        raise NotImplementedError("fromstring() has been removed. "
                                  "Please call frombytes() instead.")

    def load(self):
        """
        Allocates storage for the image and loads the pixel data.  In
        normal cases, you don't need to call this method, since the
        Image class automatically loads an opened image when it is
        accessed for the first time.

        If the file associated with the image was opened by Pillow, then this
        method will close it. The exception to this is if the image has
        multiple frames, in which case the file will be left open for seek
        operations. See :ref:`file-handling` for more information.

        :returns: An image access object.
        :rtype: :ref:`PixelAccess` or :py:class:`PIL.PyAccess`
        """
        if self.im and self.palette and self.palette.dirty:
            # realize palette
            self.im.putpalette(*self.palette.getdata())
            self.palette.dirty = 0
            self.palette.mode = "RGB"
            self.palette.rawmode = None
            if "transparency" in self.info:
                if isinstance(self.info["transparency"], int):
                    self.im.putpalettealpha(self.info["transparency"], 0)
                else:
                    self.im.putpalettealphas(self.info["transparency"])
                self.palette.mode = "RGBA"

        if self.im:
            if cffi and USE_CFFI_ACCESS:
                if self.pyaccess:
                    return self.pyaccess
                from . import PyAccess
                self.pyaccess = PyAccess.new(self, self.readonly)
                if self.pyaccess:
                    return self.pyaccess
            return self.im.pixel_access(self.readonly)

    def verify(self):
        """
        Verifies the contents of a file. For data read from a file, this
        method attempts to determine if the file is broken, without
        actually decoding the image data.  If this method finds any
        problems, it raises suitable exceptions.  If you need to load
        the image after using this method, you must reopen the image
        file.
        """
        pass

    def convert(self, mode=None, matrix=None, dither=None,
                palette=WEB, colors=256):
        """
        Returns a converted copy of this image. For the "P" mode, this
        method translates pixels through the palette.  If mode is
        omitted, a mode is chosen so that all information in the image
        and the palette can be represented without a palette.

        The current version supports all possible conversions between
        "L", "RGB" and "CMYK." The **matrix** argument only supports "L"
        and "RGB".

        When translating a color image to greyscale (mode "L"),
        the library uses the ITU-R 601-2 luma transform::

            L = R * 299/1000 + G * 587/1000 + B * 114/1000

        The default method of converting a greyscale ("L") or "RGB"
        image into a bilevel (mode "1") image uses Floyd-Steinberg
        dither to approximate the original image luminosity levels. If
        dither is NONE, all values larger than 128 are set to 255 (white),
        all other values to 0 (black). To use other thresholds, use the
        :py:meth:`~PIL.Image.Image.point` method.

        When converting from "RGBA" to "P" without a **matrix** argument,
        this passes the operation to :py:meth:`~PIL.Image.Image.quantize`,
        and **dither** and **palette** are ignored.

        :param mode: The requested mode. See: :ref:`concept-modes`.
        :param matrix: An optional conversion matrix.  If given, this
           should be 4- or 12-tuple containing floating point values.
        :param dither: Dithering method, used when converting from
           mode "RGB" to "P" or from "RGB" or "L" to "1".
           Available methods are NONE or FLOYDSTEINBERG (default).
           Note that this is not used when **matrix** is supplied.
        :param palette: Palette to use when converting from mode "RGB"
           to "P".  Available palettes are WEB or ADAPTIVE.
        :param colors: Number of colors to use for the ADAPTIVE palette.
           Defaults to 256.
        :rtype: :py:class:`~PIL.Image.Image`
        :returns: An :py:class:`~PIL.Image.Image` object.
        """

        self.load()

        if not mode and self.mode == "P":
            # determine default mode
            if self.palette:
                mode = self.palette.mode
            else:
                mode = "RGB"
        if not mode or (mode == self.mode and not matrix):
            return self.copy()

        has_transparency = self.info.get('transparency') is not None
        if matrix:
            # matrix conversion
            if mode not in ("L", "RGB"):
                raise ValueError("illegal conversion")
            im = self.im.convert_matrix(mode, matrix)
            new = self._new(im)
            if has_transparency and self.im.bands == 3:
                transparency = new.info['transparency']

                def convert_transparency(m, v):
                    v = m[0]*v[0] + m[1]*v[1] + m[2]*v[2] + m[3]*0.5
                    return max(0, min(255, int(v)))
                if mode == "L":
                    transparency = convert_transparency(matrix, transparency)
                elif len(mode) == 3:
                    transparency = tuple([
                        convert_transparency(matrix[i*4:i*4+4], transparency)
                        for i in range(0, len(transparency))
                    ])
                new.info['transparency'] = transparency
            return new

        if mode == "P" and self.mode == "RGBA":
            return self.quantize(colors)

        trns = None
        delete_trns = False
        # transparency handling
        if has_transparency:
            if self.mode in ('L', 'RGB') and mode == 'RGBA':
                # Use transparent conversion to promote from transparent
                # color to an alpha channel.
                new_im = self._new(self.im.convert_transparent(
                    mode, self.info['transparency']))
                del(new_im.info['transparency'])
                return new_im
            elif self.mode in ('L', 'RGB', 'P') and mode in ('L', 'RGB', 'P'):
                t = self.info['transparency']
                if isinstance(t, bytes):
                    # Dragons. This can't be represented by a single color
                    warnings.warn('Palette images with Transparency  ' +
                                  ' expressed in bytes should be converted ' +
                                  'to RGBA images')
                    delete_trns = True
                else:
                    # get the new transparency color.
                    # use existing conversions
                    trns_im = Image()._new(core.new(self.mode, (1, 1)))
                    if self.mode == 'P':
                        trns_im.putpalette(self.palette)
                        if isinstance(t, tuple):
                            try:
                                t = trns_im.palette.getcolor(t)
                            except Exception:
                                raise ValueError("Couldn't allocate a palette "
                                                 "color for transparency")
                    trns_im.putpixel((0, 0), t)

                    if mode in ('L', 'RGB'):
                        trns_im = trns_im.convert(mode)
                    else:
                        # can't just retrieve the palette number, got to do it
                        # after quantization.
                        trns_im = trns_im.convert('RGB')
                    trns = trns_im.getpixel((0, 0))

            elif self.mode == 'P' and mode == 'RGBA':
                t = self.info['transparency']
                delete_trns = True

                if isinstance(t, bytes):
                    self.im.putpalettealphas(t)
                elif isinstance(t, int):
                    self.im.putpalettealpha(t, 0)
                else:
                    raise ValueError("Transparency for P mode should" +
                                     " be bytes or int")

        if mode == "P" and palette == ADAPTIVE:
            im = self.im.quantize(colors)
            new = self._new(im)
            from . import ImagePalette
            new.palette = ImagePalette.raw("RGB", new.im.getpalette("RGB"))
            if delete_trns:
                # This could possibly happen if we requantize to fewer colors.
                # The transparency would be totally off in that case.
                del(new.info['transparency'])
            if trns is not None:
                try:
                    new.info['transparency'] = new.palette.getcolor(trns)
                except Exception:
                    # if we can't make a transparent color, don't leave the old
                    # transparency hanging around to mess us up.
                    del(new.info['transparency'])
                    warnings.warn("Couldn't allocate palette entry " +
                                  "for transparency")
            return new

        # colorspace conversion
        if dither is None:
            dither = FLOYDSTEINBERG

        try:
            im = self.im.convert(mode, dither)
        except ValueError:
            try:
                # normalize source image and try again
                im = self.im.convert(getmodebase(self.mode))
                im = im.convert(mode, dither)
            except KeyError:
                raise ValueError("illegal conversion")

        new_im = self._new(im)
        if delete_trns:
            # crash fail if we leave a bytes transparency in an rgb/l mode.
            del(new_im.info['transparency'])
        if trns is not None:
            if new_im.mode == 'P':
                try:
                    new_im.info['transparency'] = new_im.palette.getcolor(trns)
                except Exception:
                    del(new_im.info['transparency'])
                    warnings.warn("Couldn't allocate palette entry " +
                                  "for transparency")
            else:
                new_im.info['transparency'] = trns
        return new_im

    def quantize(self, colors=256, method=None, kmeans=0, palette=None):
        """
        Convert the image to 'P' mode with the specified number
        of colors.

        :param colors: The desired number of colors, <= 256
        :param method: 0 = median cut
                       1 = maximum coverage
                       2 = fast octree
                       3 = libimagequant
        :param kmeans: Integer
        :param palette: Quantize to the palette of given
                        :py:class:`PIL.Image.Image`.
        :returns: A new image

        """

        self.load()

        if method is None:
            # defaults:
            method = 0
            if self.mode == 'RGBA':
                method = 2

        if self.mode == 'RGBA' and method not in (2, 3):
            # Caller specified an invalid mode.
            raise ValueError(
                'Fast Octree (method == 2) and libimagequant (method == 3) ' +
                'are the only valid methods for quantizing RGBA images')

        if palette:
            # use palette from reference image
            palette.load()
            if palette.mode != "P":
                raise ValueError("bad mode for palette image")
            if self.mode != "RGB" and self.mode != "L":
                raise ValueError(
                    "only RGB or L mode images can be quantized to a palette"
                    )
            im = self.im.convert("P", 1, palette.im)
            return self._new(im)

        return self._new(self.im.quantize(colors, method, kmeans))

    def copy(self):
        """
        Copies this image. Use this method if you wish to paste things
        into an image, but still retain the original.

        :rtype: :py:class:`~PIL.Image.Image`
        :returns: An :py:class:`~PIL.Image.Image` object.
        """
        self.load()
        return self._new(self.im.copy())

    __copy__ = copy

    def crop(self, box=None):
        """
        Returns a rectangular region from this image. The box is a
        4-tuple defining the left, upper, right, and lower pixel
        coordinate. See :ref:`coordinate-system`.

        Note: Prior to Pillow 3.4.0, this was a lazy operation.

        :param box: The crop rectangle, as a (left, upper, right, lower)-tuple.
        :rtype: :py:class:`~PIL.Image.Image`
        :returns: An :py:class:`~PIL.Image.Image` object.
        """

        if box is None:
            return self.copy()

        self.load()
        return self._new(self._crop(self.im, box))

    def _crop(self, im, box):
        """
        Returns a rectangular region from the core image object im.

        This is equivalent to calling im.crop((x0, y0, x1, y1)), but
        includes additional sanity checks.

        :param im: a core image object
        :param box: The crop rectangle, as a (left, upper, right, lower)-tuple.
        :returns: A core image object.
        """

        x0, y0, x1, y1 = map(int, map(round, box))

        absolute_values = (abs(x1 - x0), abs(y1 - y0))

        _decompression_bomb_check(absolute_values)

        return im.crop((x0, y0, x1, y1))

    def draft(self, mode, size):
        """
        Configures the image file loader so it returns a version of the
        image that as closely as possible matches the given mode and
        size.  For example, you can use this method to convert a color
        JPEG to greyscale while loading it, or to extract a 128x192
        version from a PCD file.

        Note that this method modifies the :py:class:`~PIL.Image.Image` object
        in place.  If the image has already been loaded, this method has no
        effect.

        Note: This method is not implemented for most images. It is
        currently implemented only for JPEG and PCD images.

        :param mode: The requested mode.
        :param size: The requested size.
        """
        pass

    def _expand(self, xmargin, ymargin=None):
        if ymargin is None:
            ymargin = xmargin
        self.load()
        return self._new(self.im.expand(xmargin, ymargin, 0))

    def filter(self, filter):
        """
        Filters this image using the given filter.  For a list of
        available filters, see the :py:mod:`~PIL.ImageFilter` module.

        :param filter: Filter kernel.
        :returns: An :py:class:`~PIL.Image.Image` object.  """

        from . import ImageFilter

        self.load()

        if isinstance(filter, Callable):
            filter = filter()
        if not hasattr(filter, "filter"):
            raise TypeError("filter argument should be ImageFilter.Filter " +
                            "instance or class")

        multiband = isinstance(filter, ImageFilter.MultibandFilter)
        if self.im.bands == 1 or multiband:
            return self._new(filter.filter(self.im))

        ims = []
        for c in range(self.im.bands):
            ims.append(self._new(filter.filter(self.im.getband(c))))
        return merge(self.mode, ims)

    def getbands(self):
        """
        Returns a tuple containing the name of each band in this image.
        For example, **getbands** on an RGB image returns ("R", "G", "B").

        :returns: A tuple containing band names.
        :rtype: tuple
        """
        return ImageMode.getmode(self.mode).bands

    def getbbox(self):
        """
        Calculates the bounding box of the non-zero regions in the
        image.

        :returns: The bounding box is returned as a 4-tuple defining the
           left, upper, right, and lower pixel coordinate. See
           :ref:`coordinate-system`. If the image is completely empty, this
           method returns None.

        """

        self.load()
        return self.im.getbbox()

    def getcolors(self, maxcolors=256):
        """
        Returns a list of colors used in this image.

        :param maxcolors: Maximum number of colors.  If this number is
           exceeded, this method returns None.  The default limit is
           256 colors.
        :returns: An unsorted list of (count, pixel) values.
        """

        self.load()
        if self.mode in ("1", "L", "P"):
            h = self.im.histogram()
            out = []
            for i in range(256):
                if h[i]:
                    out.append((h[i], i))
            if len(out) > maxcolors:
                return None
            return out
        return self.im.getcolors(maxcolors)

    def getdata(self, band=None):
        """
        Returns the contents of this image as a sequence object
        containing pixel values.  The sequence object is flattened, so
        that values for line one follow directly after the values of
        line zero, and so on.

        Note that the sequence object returned by this method is an
        internal PIL data type, which only supports certain sequence
        operations.  To convert it to an ordinary sequence (e.g. for
        printing), use **list(im.getdata())**.

        :param band: What band to return.  The default is to return
           all bands.  To return a single band, pass in the index
           value (e.g. 0 to get the "R" band from an "RGB" image).
        :returns: A sequence-like object.
        """

        self.load()
        if band is not None:
            return self.im.getband(band)
        return self.im  # could be abused

    def getextrema(self):
        """
        Gets the the minimum and maximum pixel values for each band in
        the image.

        :returns: For a single-band image, a 2-tuple containing the
           minimum and maximum pixel value.  For a multi-band image,
           a tuple containing one 2-tuple for each band.
        """

        self.load()
        if self.im.bands > 1:
            extrema = []
            for i in range(self.im.bands):
                extrema.append(self.im.getband(i).getextrema())
            return tuple(extrema)
        return self.im.getextrema()

    def getim(self):
        """
        Returns a capsule that points to the internal image memory.

        :returns: A capsule object.
        """

        self.load()
        return self.im.ptr

    def getpalette(self):
        """
        Returns the image palette as a list.

        :returns: A list of color values [r, g, b, ...], or None if the
           image has no palette.
        """

        self.load()
        try:
            if py3:
                return list(self.im.getpalette())
            else:
                return [i8(c) for c in self.im.getpalette()]
        except ValueError:
            return None  # no palette

    def getpixel(self, xy):
        """
        Returns the pixel value at a given position.

        :param xy: The coordinate, given as (x, y). See
           :ref:`coordinate-system`.
        :returns: The pixel value.  If the image is a multi-layer image,
           this method returns a tuple.
        """

        self.load()
        if self.pyaccess:
            return self.pyaccess.getpixel(xy)
        return self.im.getpixel(xy)

    def getprojection(self):
        """
        Get projection to x and y axes

        :returns: Two sequences, indicating where there are non-zero
            pixels along the X-axis and the Y-axis, respectively.
        """

        self.load()
        x, y = self.im.getprojection()
        return [i8(c) for c in x], [i8(c) for c in y]

    def histogram(self, mask=None, extrema=None):
        """
        Returns a histogram for the image. The histogram is returned as
        a list of pixel counts, one for each pixel value in the source
        image. If the image has more than one band, the histograms for
        all bands are concatenated (for example, the histogram for an
        "RGB" image contains 768 values).

        A bilevel image (mode "1") is treated as a greyscale ("L") image
        by this method.

        If a mask is provided, the method returns a histogram for those
        parts of the image where the mask image is non-zero. The mask
        image must have the same size as the image, and be either a
        bi-level image (mode "1") or a greyscale image ("L").

        :param mask: An optional mask.
        :returns: A list containing pixel counts.
        """
        self.load()
        if mask:
            mask.load()
            return self.im.histogram((0, 0), mask.im)
        if self.mode in ("I", "F"):
            if extrema is None:
                extrema = self.getextrema()
            return self.im.histogram(extrema)
        return self.im.histogram()

    def offset(self, xoffset, yoffset=None):
        raise NotImplementedError("offset() has been removed. "
                                  "Please call ImageChops.offset() instead.")

    def paste(self, im, box=None, mask=None):
        """
        Pastes another image into this image. The box argument is either
        a 2-tuple giving the upper left corner, a 4-tuple defining the
        left, upper, right, and lower pixel coordinate, or None (same as
        (0, 0)). See :ref:`coordinate-system`. If a 4-tuple is given, the size
        of the pasted image must match the size of the region.

        If the modes don't match, the pasted image is converted to the mode of
        this image (see the :py:meth:`~PIL.Image.Image.convert` method for
        details).

        Instead of an image, the source can be a integer or tuple
        containing pixel values.  The method then fills the region
        with the given color.  When creating RGB images, you can
        also use color strings as supported by the ImageColor module.

        If a mask is given, this method updates only the regions
        indicated by the mask.  You can use either "1", "L" or "RGBA"
        images (in the latter case, the alpha band is used as mask).
        Where the mask is 255, the given image is copied as is.  Where
        the mask is 0, the current value is preserved.  Intermediate
        values will mix the two images together, including their alpha
        channels if they have them.

        See :py:meth:`~PIL.Image.Image.alpha_composite` if you want to
        combine images with respect to their alpha channels.

        :param im: Source image or pixel value (integer or tuple).
        :param box: An optional 4-tuple giving the region to paste into.
           If a 2-tuple is used instead, it's treated as the upper left
           corner.  If omitted or None, the source is pasted into the
           upper left corner.

           If an image is given as the second argument and there is no
           third, the box defaults to (0, 0), and the second argument
           is interpreted as a mask image.
        :param mask: An optional mask image.
        """

        if isImageType(box) and mask is None:
            # abbreviated paste(im, mask) syntax
            mask = box
            box = None

        if box is None:
            box = (0, 0)

        if len(box) == 2:
            # upper left corner given; get size from image or mask
            if isImageType(im):
                size = im.size
            elif isImageType(mask):
                size = mask.size
            else:
                # FIXME: use self.size here?
                raise ValueError(
                    "cannot determine region size; use 4-item box"
                    )
            box += (box[0]+size[0], box[1]+size[1])

        if isStringType(im):
            from . import ImageColor
            im = ImageColor.getcolor(im, self.mode)

        elif isImageType(im):
            im.load()
            if self.mode != im.mode:
                if self.mode != "RGB" or im.mode not in ("RGBA", "RGBa"):
                    # should use an adapter for this!
                    im = im.convert(self.mode)
            im = im.im

        self._ensure_mutable()

        if mask:
            mask.load()
            self.im.paste(im, box, mask.im)
        else:
            self.im.paste(im, box)

    def alpha_composite(self, im, dest=(0, 0), source=(0, 0)):
        """ 'In-place' analog of Image.alpha_composite. Composites an image
        onto this image.

        :param im: image to composite over this one
        :param dest: Optional 2 tuple (left, top) specifying the upper
          left corner in this (destination) image.
        :param source: Optional 2 (left, top) tuple for the upper left
          corner in the overlay source image, or 4 tuple (left, top, right,
          bottom) for the bounds of the source rectangle

        Performance Note: Not currently implemented in-place in the core layer.
        """

        if not isinstance(source, (list, tuple)):
            raise ValueError("Source must be a tuple")
        if not isinstance(dest, (list, tuple)):
            raise ValueError("Destination must be a tuple")
        if not len(source) in (2, 4):
            raise ValueError("Source must be a 2 or 4-tuple")
        if not len(dest) == 2:
            raise ValueError("Destination must be a 2-tuple")
        if min(source) < 0:
            raise ValueError("Source must be non-negative")
        if min(dest) < 0:
            raise ValueError("Destination must be non-negative")

        if len(source) == 2:
            source = source + im.size

        # over image, crop if it's not the whole thing.
        if source == (0, 0) + im.size:
            overlay = im
        else:
            overlay = im.crop(source)

        # target for the paste
        box = dest + (dest[0] + overlay.width, dest[1] + overlay.height)

        # destination image. don't copy if we're using the whole image.
        if box == (0, 0) + self.size:
            background = self
        else:
            background = self.crop(box)

        result = alpha_composite(background, overlay)
        self.paste(result, box)

    def point(self, lut, mode=None):
        """
        Maps this image through a lookup table or function.

        :param lut: A lookup table, containing 256 (or 65536 if
           self.mode=="I" and mode == "L") values per band in the
           image.  A function can be used instead, it should take a
           single argument. The function is called once for each
           possible pixel value, and the resulting table is applied to
           all bands of the image.
        :param mode: Output mode (default is same as input).  In the
           current version, this can only be used if the source image
           has mode "L" or "P", and the output has mode "1" or the
           source image mode is "I" and the output mode is "L".
        :returns: An :py:class:`~PIL.Image.Image` object.
        """

        self.load()

        if isinstance(lut, ImagePointHandler):
            return lut.point(self)

        if callable(lut):
            # if it isn't a list, it should be a function
            if self.mode in ("I", "I;16", "F"):
                # check if the function can be used with point_transform
                # UNDONE wiredfool -- I think this prevents us from ever doing
                # a gamma function point transform on > 8bit images.
                scale, offset = _getscaleoffset(lut)
                return self._new(self.im.point_transform(scale, offset))
            # for other modes, convert the function to a table
            lut = [lut(i) for i in range(256)] * self.im.bands

        if self.mode == "F":
            # FIXME: _imaging returns a confusing error message for this case
            raise ValueError("point operation not supported for this mode")

        return self._new(self.im.point(lut, mode))

    def putalpha(self, alpha):
        """
        Adds or replaces the alpha layer in this image.  If the image
        does not have an alpha layer, it's converted to "LA" or "RGBA".
        The new layer must be either "L" or "1".

        :param alpha: The new alpha layer.  This can either be an "L" or "1"
           image having the same size as this image, or an integer or
           other color value.
        """

        self._ensure_mutable()

        if self.mode not in ("LA", "RGBA"):
            # attempt to promote self to a matching alpha mode
            try:
                mode = getmodebase(self.mode) + "A"
                try:
                    self.im.setmode(mode)
                except (AttributeError, ValueError):
                    # do things the hard way
                    im = self.im.convert(mode)
                    if im.mode not in ("LA", "RGBA"):
                        raise ValueError  # sanity check
                    self.im = im
                self.pyaccess = None
                self.mode = self.im.mode
            except (KeyError, ValueError):
                raise ValueError("illegal image mode")

        if self.mode == "LA":
            band = 1
        else:
            band = 3

        if isImageType(alpha):
            # alpha layer
            if alpha.mode not in ("1", "L"):
                raise ValueError("illegal image mode")
            alpha.load()
            if alpha.mode == "1":
                alpha = alpha.convert("L")
        else:
            # constant alpha
            try:
                self.im.fillband(band, alpha)
            except (AttributeError, ValueError):
                # do things the hard way
                alpha = new("L", self.size, alpha)
            else:
                return

        self.im.putband(alpha.im, band)

    def putdata(self, data, scale=1.0, offset=0.0):
        """
        Copies pixel data to this image.  This method copies data from a
        sequence object into the image, starting at the upper left
        corner (0, 0), and continuing until either the image or the
        sequence ends.  The scale and offset values are used to adjust
        the sequence values: **pixel = value*scale + offset**.

        :param data: A sequence object.
        :param scale: An optional scale value.  The default is 1.0.
        :param offset: An optional offset value.  The default is 0.0.
        """

        self._ensure_mutable()

        self.im.putdata(data, scale, offset)

    def putpalette(self, data, rawmode="RGB"):
        """
        Attaches a palette to this image.  The image must be a "P" or
        "L" image, and the palette sequence must contain 768 integer
        values, where each group of three values represent the red,
        green, and blue values for the corresponding pixel
        index. Instead of an integer sequence, you can use an 8-bit
        string.

        :param data: A palette sequence (either a list or a string).
        :param rawmode: The raw mode of the palette.
        """
        from . import ImagePalette

        if self.mode not in ("L", "P"):
            raise ValueError("illegal image mode")
        self.load()
        if isinstance(data, ImagePalette.ImagePalette):
            palette = ImagePalette.raw(data.rawmode, data.palette)
        else:
            if not isinstance(data, bytes):
                if py3:
                    data = bytes(data)
                else:
                    data = "".join(chr(x) for x in data)
            palette = ImagePalette.raw(rawmode, data)
        self.mode = "P"
        self.palette = palette
        self.palette.mode = "RGB"
        self.load()  # install new palette

    def putpixel(self, xy, value):
        """
        Modifies the pixel at the given position. The color is given as
        a single numerical value for single-band images, and a tuple for
        multi-band images. In addition to this, RGB and RGBA tuples are
        accepted for P images.

        Note that this method is relatively slow.  For more extensive changes,
        use :py:meth:`~PIL.Image.Image.paste` or the :py:mod:`~PIL.ImageDraw`
        module instead.

        See:

        * :py:meth:`~PIL.Image.Image.paste`
        * :py:meth:`~PIL.Image.Image.putdata`
        * :py:mod:`~PIL.ImageDraw`

        :param xy: The pixel coordinate, given as (x, y). See
           :ref:`coordinate-system`.
        :param value: The pixel value.
        """

        if self.readonly:
            self._copy()
        self.load()

        if self.pyaccess:
            return self.pyaccess.putpixel(xy, value)

        if self.mode == "P" and \
           isinstance(value, (list, tuple)) and len(value) in [3, 4]:
            # RGB or RGBA value for a P image
            value = self.palette.getcolor(value)
        return self.im.putpixel(xy, value)

    def remap_palette(self, dest_map, source_palette=None):
        """
        Rewrites the image to reorder the palette.

        :param dest_map: A list of indexes into the original palette.
           e.g. [1,0] would swap a two item palette, and list(range(255))
           is the identity transform.
        :param source_palette: Bytes or None.
        :returns:  An :py:class:`~PIL.Image.Image` object.

        """
        from . import ImagePalette

        if self.mode not in ("L", "P"):
            raise ValueError("illegal image mode")

        if source_palette is None:
            if self.mode == "P":
                real_source_palette = self.im.getpalette("RGB")[:768]
            else:  # L-mode
                real_source_palette = bytearray(i//3 for i in range(768))
        else:
            real_source_palette = source_palette

        palette_bytes = b""
        new_positions = [0]*256

        # pick only the used colors from the palette
        for i, oldPosition in enumerate(dest_map):
            palette_bytes += real_source_palette[oldPosition*3:oldPosition*3+3]
            new_positions[oldPosition] = i

        # replace the palette color id of all pixel with the new id

        # Palette images are [0..255], mapped through a 1 or 3
        # byte/color map.  We need to remap the whole image
        # from palette 1 to palette 2. New_positions is
        # an array of indexes into palette 1.  Palette 2 is
        # palette 1 with any holes removed.

        # We're going to leverage the convert mechanism to use the
        # C code to remap the image from palette 1 to palette 2,
        # by forcing the source image into 'L' mode and adding a
        # mapping 'L' mode palette, then converting back to 'L'
        # sans palette thus converting the image bytes, then
        # assigning the optimized RGB palette.

        # perf reference, 9500x4000 gif, w/~135 colors
        # 14 sec prepatch, 1 sec postpatch with optimization forced.

        mapping_palette = bytearray(new_positions)

        m_im = self.copy()
        m_im.mode = 'P'

        m_im.palette = ImagePalette.ImagePalette("RGB",
                                                 palette=mapping_palette*3,
                                                 size=768)
        # possibly set palette dirty, then
        # m_im.putpalette(mapping_palette, 'L')  # converts to 'P'
        # or just force it.
        # UNDONE -- this is part of the general issue with palettes
        m_im.im.putpalette(*m_im.palette.getdata())

        m_im = m_im.convert('L')

        # Internally, we require 768 bytes for a palette.
        new_palette_bytes = (palette_bytes +
                             (768 - len(palette_bytes)) * b'\x00')
        m_im.putpalette(new_palette_bytes)
        m_im.palette = ImagePalette.ImagePalette("RGB",
                                                 palette=palette_bytes,
                                                 size=len(palette_bytes))

        return m_im

    def resize(self, size, resample=NEAREST, box=None):
        """
        Returns a resized copy of this image.

        :param size: The requested size in pixels, as a 2-tuple:
           (width, height).
        :param resample: An optional resampling filter.  This can be
           one of :py:attr:`PIL.Image.NEAREST`, :py:attr:`PIL.Image.BOX`,
           :py:attr:`PIL.Image.BILINEAR`, :py:attr:`PIL.Image.HAMMING`,
           :py:attr:`PIL.Image.BICUBIC` or :py:attr:`PIL.Image.LANCZOS`.
           If omitted, or if the image has mode "1" or "P", it is
           set :py:attr:`PIL.Image.NEAREST`.
           See: :ref:`concept-filters`.
        :param box: An optional 4-tuple of floats giving the region
           of the source image which should be scaled.
           The values should be within (0, 0, width, height) rectangle.
           If omitted or None, the entire source is used.
        :returns: An :py:class:`~PIL.Image.Image` object.
        """

        if resample not in (
                NEAREST, BILINEAR, BICUBIC, LANCZOS, BOX, HAMMING,
        ):
            raise ValueError("unknown resampling filter")

        size = tuple(size)

        if box is None:
            box = (0, 0) + self.size
        else:
            box = tuple(box)

        if self.size == size and box == (0, 0) + self.size:
            return self.copy()

        if self.mode in ("1", "P"):
            resample = NEAREST

        if self.mode in ['LA', 'RGBA']:
            im = self.convert(self.mode[:-1]+'a')
            im = im.resize(size, resample, box)
            return im.convert(self.mode)

        self.load()

        return self._new(self.im.resize(size, resample, box))

    def rotate(self, angle, resample=NEAREST, expand=0, center=None,
               translate=None, fillcolor=None):
        """
        Returns a rotated copy of this image.  This method returns a
        copy of this image, rotated the given number of degrees counter
        clockwise around its centre.

        :param angle: In degrees counter clockwise.
        :param resample: An optional resampling filter.  This can be
           one of :py:attr:`PIL.Image.NEAREST` (use nearest neighbour),
           :py:attr:`PIL.Image.BILINEAR` (linear interpolation in a 2x2
           environment), or :py:attr:`PIL.Image.BICUBIC`
           (cubic spline interpolation in a 4x4 environment).
           If omitted, or if the image has mode "1" or "P", it is
           set :py:attr:`PIL.Image.NEAREST`. See :ref:`concept-filters`.
        :param expand: Optional expansion flag.  If true, expands the output
           image to make it large enough to hold the entire rotated image.
           If false or omitted, make the output image the same size as the
           input image.  Note that the expand flag assumes rotation around
           the center and no translation.
        :param center: Optional center of rotation (a 2-tuple).  Origin is
           the upper left corner.  Default is the center of the image.
        :param translate: An optional post-rotate translation (a 2-tuple).
        :param fillcolor: An optional color for area outside the rotated image.
        :returns: An :py:class:`~PIL.Image.Image` object.
        """

        angle = angle % 360.0

        # Fast paths regardless of filter, as long as we're not
        # translating or changing the center.
        if not (center or translate):
            if angle == 0:
                return self.copy()
            if angle == 180:
                return self.transpose(ROTATE_180)
            if angle == 90 and expand:
                return self.transpose(ROTATE_90)
            if angle == 270 and expand:
                return self.transpose(ROTATE_270)

        # Calculate the affine matrix.  Note that this is the reverse
        # transformation (from destination image to source) because we
        # want to interpolate the (discrete) destination pixel from
        # the local area around the (floating) source pixel.

        # The matrix we actually want (note that it operates from the right):
        # (1, 0, tx)   (1, 0, cx)   ( cos a, sin a, 0)   (1, 0, -cx)
        # (0, 1, ty) * (0, 1, cy) * (-sin a, cos a, 0) * (0, 1, -cy)
        # (0, 0,  1)   (0, 0,  1)   (     0,     0, 1)   (0, 0,   1)

        # The reverse matrix is thus:
        # (1, 0, cx)   ( cos -a, sin -a, 0)   (1, 0, -cx)   (1, 0, -tx)
        # (0, 1, cy) * (-sin -a, cos -a, 0) * (0, 1, -cy) * (0, 1, -ty)
        # (0, 0,  1)   (      0,      0, 1)   (0, 0,   1)   (0, 0,   1)

        # In any case, the final translation may be updated at the end to
        # compensate for the expand flag.

        w, h = self.size

        if translate is None:
            post_trans = (0, 0)
        else:
            post_trans = translate
        if center is None:
            # FIXME These should be rounded to ints?
            rotn_center = (w / 2.0, h / 2.0)
        else:
            rotn_center = center

        angle = - math.radians(angle)
        matrix = [
            round(math.cos(angle), 15), round(math.sin(angle), 15), 0.0,
            round(-math.sin(angle), 15), round(math.cos(angle), 15), 0.0
        ]

        def transform(x, y, matrix):
            (a, b, c, d, e, f) = matrix
            return a*x + b*y + c, d*x + e*y + f

        matrix[2], matrix[5] = transform(-rotn_center[0] - post_trans[0],
                                         -rotn_center[1] - post_trans[1],
                                         matrix)
        matrix[2] += rotn_center[0]
        matrix[5] += rotn_center[1]

        if expand:
            # calculate output size
            xx = []
            yy = []
            for x, y in ((0, 0), (w, 0), (w, h), (0, h)):
                x, y = transform(x, y, matrix)
                xx.append(x)
                yy.append(y)
            nw = int(math.ceil(max(xx)) - math.floor(min(xx)))
            nh = int(math.ceil(max(yy)) - math.floor(min(yy)))

            # We multiply a translation matrix from the right.  Because of its
            # special form, this is the same as taking the image of the
            # translation vector as new translation vector.
            matrix[2], matrix[5] = transform(-(nw - w) / 2.0,
                                             -(nh - h) / 2.0,
                                             matrix)
            w, h = nw, nh

        return self.transform((w, h), AFFINE, matrix, resample,
                              fillcolor=fillcolor)

    def save(self, fp, format=None, **params):
        """
        Saves this image under the given filename.  If no format is
        specified, the format to use is determined from the filename
        extension, if possible.

        Keyword options can be used to provide additional instructions
        to the writer. If a writer doesn't recognise an option, it is
        silently ignored. The available options are described in the
        :doc:`image format documentation
        <../handbook/image-file-formats>` for each writer.

        You can use a file object instead of a filename. In this case,
        you must always specify the format. The file object must
        implement the ``seek``, ``tell``, and ``write``
        methods, and be opened in binary mode.

        :param fp: A filename (string), pathlib.Path object or file object.
        :param format: Optional format override.  If omitted, the
           format to use is determined from the filename extension.
           If a file object was used instead of a filename, this
           parameter should always be used.
        :param params: Extra parameters to the image writer.
        :returns: None
        :exception ValueError: If the output format could not be determined
           from the file name.  Use the format option to solve this.
        :exception IOError: If the file could not be written.  The file
           may have been created, and may contain partial data.
        """

        filename = ""
        open_fp = False
        if isPath(fp):
            filename = fp
            open_fp = True
        elif HAS_PATHLIB and isinstance(fp, Path):
            filename = str(fp)
            open_fp = True
        if not filename and hasattr(fp, "name") and isPath(fp.name):
            # only set the name for metadata purposes
            filename = fp.name

        # may mutate self!
        self.load()

        save_all = params.pop('save_all', False)
        self.encoderinfo = params
        self.encoderconfig = ()

        preinit()

        ext = os.path.splitext(filename)[1].lower()

        if not format:
            if ext not in EXTENSION:
                init()
            try:
                format = EXTENSION[ext]
            except KeyError:
                raise ValueError('unknown file extension: {}'.format(ext))

        if format.upper() not in SAVE:
            init()
        if save_all:
            save_handler = SAVE_ALL[format.upper()]
        else:
            save_handler = SAVE[format.upper()]

        if open_fp:
            if params.get('append', False):
                fp = builtins.open(filename, "r+b")
            else:
                # Open also for reading ("+"), because TIFF save_all
                # writer needs to go back and edit the written data.
                fp = builtins.open(filename, "w+b")

        try:
            save_handler(self, fp, filename)
        finally:
            # do what we can to clean up
            if open_fp:
                fp.close()

    def seek(self, frame):
        """
        Seeks to the given frame in this sequence file. If you seek
        beyond the end of the sequence, the method raises an
        **EOFError** exception. When a sequence file is opened, the
        library automatically seeks to frame 0.

        Note that in the current version of the library, most sequence
        formats only allows you to seek to the next frame.

        See :py:meth:`~PIL.Image.Image.tell`.

        :param frame: Frame number, starting at 0.
        :exception EOFError: If the call attempts to seek beyond the end
            of the sequence.
        """

        # overridden by file handlers
        if frame != 0:
            raise EOFError

    def show(self, title=None, command=None):
        """
        Displays this image. This method is mainly intended for
        debugging purposes.

        On Unix platforms, this method saves the image to a temporary
        PPM file, and calls either the **xv** utility or the **display**
        utility, depending on which one can be found.

        On macOS, this method saves the image to a temporary BMP file, and
        opens it with the native Preview application.

        On Windows, it saves the image to a temporary BMP file, and uses
        the standard BMP display utility to show it (usually Paint).

        :param title: Optional title to use for the image window,
           where possible.
        :param command: command used to show the image
        """

        _show(self, title=title, command=command)

    def split(self):
        """
        Split this image into individual bands. This method returns a
        tuple of individual image bands from an image. For example,
        splitting an "RGB" image creates three new images each
        containing a copy of one of the original bands (red, green,
        blue).

        If you need only one band, :py:meth:`~PIL.Image.Image.getchannel`
        method can be more convenient and faster.

        :returns: A tuple containing bands.
        """

        self.load()
        if self.im.bands == 1:
            ims = [self.copy()]
        else:
            ims = map(self._new, self.im.split())
        return tuple(ims)

    def getchannel(self, channel):
        """
        Returns an image containing a single channel of the source image.

        :param channel: What channel to return. Could be index
          (0 for "R" channel of "RGB") or channel name
          ("A" for alpha channel of "RGBA").
        :returns: An image in "L" mode.

        .. versionadded:: 4.3.0
        """
        self.load()

        if isStringType(channel):
            try:
                channel = self.getbands().index(channel)
            except ValueError:
                raise ValueError(
                    'The image has no channel "{}"'.format(channel))

        return self._new(self.im.getband(channel))

    def tell(self):
        """
        Returns the current frame number. See :py:meth:`~PIL.Image.Image.seek`.

        :returns: Frame number, starting with 0.
        """
        return 0

    def thumbnail(self, size, resample=BICUBIC):
        """
        Make this image into a thumbnail.  This method modifies the
        image to contain a thumbnail version of itself, no larger than
        the given size.  This method calculates an appropriate thumbnail
        size to preserve the aspect of the image, calls the
        :py:meth:`~PIL.Image.Image.draft` method to configure the file reader
        (where applicable), and finally resizes the image.

        Note that this function modifies the :py:class:`~PIL.Image.Image`
        object in place.  If you need to use the full resolution image as well,
        apply this method to a :py:meth:`~PIL.Image.Image.copy` of the original
        image.

        :param size: Requested size.
        :param resample: Optional resampling filter.  This can be one
           of :py:attr:`PIL.Image.NEAREST`, :py:attr:`PIL.Image.BILINEAR`,
           :py:attr:`PIL.Image.BICUBIC`, or :py:attr:`PIL.Image.LANCZOS`.
           If omitted, it defaults to :py:attr:`PIL.Image.BICUBIC`.
           (was :py:attr:`PIL.Image.NEAREST` prior to version 2.5.0)
        :returns: None
        """

        # preserve aspect ratio
        x, y = self.size
        if x > size[0]:
            y = int(max(y * size[0] / x, 1))
            x = int(size[0])
        if y > size[1]:
            x = int(max(x * size[1] / y, 1))
            y = int(size[1])
        size = x, y

        if size == self.size:
            return

        self.draft(None, size)

        im = self.resize(size, resample)

        self.im = im.im
        self.mode = im.mode
        self._size = size

        self.readonly = 0
        self.pyaccess = None

    # FIXME: the different transform methods need further explanation
    # instead of bloating the method docs, add a separate chapter.
    def transform(self, size, method, data=None, resample=NEAREST,
                  fill=1, fillcolor=None):
        """
        Transforms this image.  This method creates a new image with the
        given size, and the same mode as the original, and copies data
        to the new image using the given transform.

        :param size: The output size.
        :param method: The transformation method.  This is one of
          :py:attr:`PIL.Image.EXTENT` (cut out a rectangular subregion),
          :py:attr:`PIL.Image.AFFINE` (affine transform),
          :py:attr:`PIL.Image.PERSPECTIVE` (perspective transform),
          :py:attr:`PIL.Image.QUAD` (map a quadrilateral to a rectangle), or
          :py:attr:`PIL.Image.MESH` (map a number of source quadrilaterals
          in one operation).

          It may also be an :py:class:`~PIL.Image.ImageTransformHandler`
          object::
            class Example(Image.ImageTransformHandler):
                def transform(size, method, data, resample, fill=1):
                    # Return result

          It may also be an object with a :py:meth:`~method.getdata` method
          that returns a tuple supplying new **method** and **data** values::
            class Example(object):
                def getdata(self):
                    method = Image.EXTENT
                    data = (0, 0, 100, 100)
                    return method, data
        :param data: Extra data to the transformation method.
        :param resample: Optional resampling filter.  It can be one of
           :py:attr:`PIL.Image.NEAREST` (use nearest neighbour),
           :py:attr:`PIL.Image.BILINEAR` (linear interpolation in a 2x2
           environment), or :py:attr:`PIL.Image.BICUBIC` (cubic spline
           interpolation in a 4x4 environment). If omitted, or if the image
           has mode "1" or "P", it is set to :py:attr:`PIL.Image.NEAREST`.
        :param fill: If **method** is an
          :py:class:`~PIL.Image.ImageTransformHandler` object, this is one of
          the arguments passed to it. Otherwise, it is unused.
        :param fillcolor: Optional fill color for the area outside the
           transform in the output image.
        :returns: An :py:class:`~PIL.Image.Image` object.
        """

        if self.mode == 'LA':
            return self.convert('La').transform(
                size, method, data, resample, fill, fillcolor).convert('LA')

        if self.mode == 'RGBA':
            return self.convert('RGBa').transform(
                size, method, data, resample, fill, fillcolor).convert('RGBA')

        if isinstance(method, ImageTransformHandler):
            return method.transform(size, self, resample=resample, fill=fill)

        if hasattr(method, "getdata"):
            # compatibility w. old-style transform objects
            method, data = method.getdata()

        if data is None:
            raise ValueError("missing method data")

        im = new(self.mode, size, fillcolor)
        if method == MESH:
            # list of quads
            for box, quad in data:
                im.__transformer(box, self, QUAD, quad, resample,
                                 fillcolor is None)
        else:
            im.__transformer((0, 0)+size, self, method, data,
                             resample, fillcolor is None)

        return im

    def __transformer(self, box, image, method, data,
                      resample=NEAREST, fill=1):
        w = box[2] - box[0]
        h = box[3] - box[1]

        if method == AFFINE:
            data = data[0:6]

        elif method == EXTENT:
            # convert extent to an affine transform
            x0, y0, x1, y1 = data
            xs = float(x1 - x0) / w
            ys = float(y1 - y0) / h
            method = AFFINE
            data = (xs, 0, x0, 0, ys, y0)

        elif method == PERSPECTIVE:
            data = data[0:8]

        elif method == QUAD:
            # quadrilateral warp.  data specifies the four corners
            # given as NW, SW, SE, and NE.
            nw = data[0:2]
            sw = data[2:4]
            se = data[4:6]
            ne = data[6:8]
            x0, y0 = nw
            As = 1.0 / w
            At = 1.0 / h
            data = (x0, (ne[0]-x0)*As, (sw[0]-x0)*At,
                    (se[0]-sw[0]-ne[0]+x0)*As*At,
                    y0, (ne[1]-y0)*As, (sw[1]-y0)*At,
                    (se[1]-sw[1]-ne[1]+y0)*As*At)

        else:
            raise ValueError("unknown transformation method")

        if resample not in (NEAREST, BILINEAR, BICUBIC):
            raise ValueError("unknown resampling filter")

        image.load()

        self.load()

        if image.mode in ("1", "P"):
            resample = NEAREST

        self.im.transform2(box, image.im, method, data, resample, fill)

    def transpose(self, method):
        """
        Transpose image (flip or rotate in 90 degree steps)

        :param method: One of :py:attr:`PIL.Image.FLIP_LEFT_RIGHT`,
          :py:attr:`PIL.Image.FLIP_TOP_BOTTOM`, :py:attr:`PIL.Image.ROTATE_90`,
          :py:attr:`PIL.Image.ROTATE_180`, :py:attr:`PIL.Image.ROTATE_270`,
          :py:attr:`PIL.Image.TRANSPOSE` or :py:attr:`PIL.Image.TRANSVERSE`.
        :returns: Returns a flipped or rotated copy of this image.
        """

        self.load()
        return self._new(self.im.transpose(method))

    def effect_spread(self, distance):
        """
        Randomly spread pixels in an image.

        :param distance: Distance to spread pixels.
        """
        self.load()
        return self._new(self.im.effect_spread(distance))

    def toqimage(self):
        """Returns a QImage copy of this image"""
        from . import ImageQt
        if not ImageQt.qt_is_installed:
            raise ImportError("Qt bindings are not installed")
        return ImageQt.toqimage(self)

    def toqpixmap(self):
        """Returns a QPixmap copy of this image"""
        from . import ImageQt
        if not ImageQt.qt_is_installed:
            raise ImportError("Qt bindings are not installed")
        return ImageQt.toqpixmap(self)


# --------------------------------------------------------------------
# Abstract handlers.

class ImagePointHandler(object):
    # used as a mixin by point transforms (for use with im.point)
    pass


class ImageTransformHandler(object):
    # used as a mixin by geometry transforms (for use with im.transform)
    pass


# --------------------------------------------------------------------
# Factories

#
# Debugging

def _wedge():
    """Create greyscale wedge (for debugging only)"""

    return Image()._new(core.wedge("L"))


def _check_size(size):
    """
    Common check to enforce type and sanity check on size tuples

    :param size: Should be a 2 tuple of (width, height)
    :returns: True, or raises a ValueError
    """

    if not isinstance(size, (list, tuple)):
        raise ValueError("Size must be a tuple")
    if len(size) != 2:
        raise ValueError("Size must be a tuple of length 2")
    if size[0] < 0 or size[1] < 0:
        raise ValueError("Width and height must be >= 0")

    return True


def new(mode, size, color=0):
    """
    Creates a new image with the given mode and size.

    :param mode: The mode to use for the new image. See:
       :ref:`concept-modes`.
    :param size: A 2-tuple, containing (width, height) in pixels.
    :param color: What color to use for the image.  Default is black.
       If given, this should be a single integer or floating point value
       for single-band modes, and a tuple for multi-band modes (one value
       per band).  When creating RGB images, you can also use color
       strings as supported by the ImageColor module.  If the color is
       None, the image is not initialised.
    :returns: An :py:class:`~PIL.Image.Image` object.
    """

    _check_size(size)

    if color is None:
        # don't initialize
        return Image()._new(core.new(mode, size))

    if isStringType(color):
        # css3-style specifier

        from . import ImageColor
        color = ImageColor.getcolor(color, mode)

    return Image()._new(core.fill(mode, size, color))


def frombytes(mode, size, data, decoder_name="raw", *args):
    """
    Creates a copy of an image memory from pixel data in a buffer.

    In its simplest form, this function takes three arguments
    (mode, size, and unpacked pixel data).

    You can also use any pixel decoder supported by PIL.  For more
    information on available decoders, see the section
    :ref:`Writing Your Own File Decoder <file-decoders>`.

    Note that this function decodes pixel data only, not entire images.
    If you have an entire image in a string, wrap it in a
    :py:class:`~io.BytesIO` object, and use :py:func:`~PIL.Image.open` to load
    it.

    :param mode: The image mode. See: :ref:`concept-modes`.
    :param size: The image size.
    :param data: A byte buffer containing raw data for the given mode.
    :param decoder_name: What decoder to use.
    :param args: Additional parameters for the given decoder.
    :returns: An :py:class:`~PIL.Image.Image` object.
    """

    _check_size(size)

    # may pass tuple instead of argument list
    if len(args) == 1 and isinstance(args[0], tuple):
        args = args[0]

    if decoder_name == "raw" and args == ():
        args = mode

    im = new(mode, size)
    im.frombytes(data, decoder_name, args)
    return im


def fromstring(*args, **kw):
    raise NotImplementedError("fromstring() has been removed. " +
                              "Please call frombytes() instead.")


def frombuffer(mode, size, data, decoder_name="raw", *args):
    """
    Creates an image memory referencing pixel data in a byte buffer.

    This function is similar to :py:func:`~PIL.Image.frombytes`, but uses data
    in the byte buffer, where possible.  This means that changes to the
    original buffer object are reflected in this image).  Not all modes can
    share memory; supported modes include "L", "RGBX", "RGBA", and "CMYK".

    Note that this function decodes pixel data only, not entire images.
    If you have an entire image file in a string, wrap it in a
    **BytesIO** object, and use :py:func:`~PIL.Image.open` to load it.

    In the current version, the default parameters used for the "raw" decoder
    differs from that used for :py:func:`~PIL.Image.frombytes`.  This is a
    bug, and will probably be fixed in a future release.  The current release
    issues a warning if you do this; to disable the warning, you should provide
    the full set of parameters.  See below for details.

    :param mode: The image mode. See: :ref:`concept-modes`.
    :param size: The image size.
    :param data: A bytes or other buffer object containing raw
        data for the given mode.
    :param decoder_name: What decoder to use.
    :param args: Additional parameters for the given decoder.  For the
        default encoder ("raw"), it's recommended that you provide the
        full set of parameters::

            frombuffer(mode, size, data, "raw", mode, 0, 1)

    :returns: An :py:class:`~PIL.Image.Image` object.

    .. versionadded:: 1.1.4
    """

    _check_size(size)

    # may pass tuple instead of argument list
    if len(args) == 1 and isinstance(args[0], tuple):
        args = args[0]

    if decoder_name == "raw":
        if args == ():
            warnings.warn(
                "the frombuffer defaults may change in a future release; "
                "for portability, change the call to read:\n"
                "  frombuffer(mode, size, data, 'raw', mode, 0, 1)",
                RuntimeWarning, stacklevel=2
            )
            args = mode, 0, -1  # may change to (mode, 0, 1) post-1.1.6
        if args[0] in _MAPMODES:
            im = new(mode, (1, 1))
            im = im._new(
                core.map_buffer(data, size, decoder_name, None, 0, args)
                )
            im.readonly = 1
            return im

    return frombytes(mode, size, data, decoder_name, args)


def fromarray(obj, mode=None):
    """
    Creates an image memory from an object exporting the array interface
    (using the buffer protocol).

    If **obj** is not contiguous, then the tobytes method is called
    and :py:func:`~PIL.Image.frombuffer` is used.

    If you have an image in NumPy::

      from PIL import Image
      import numpy as np
      im = Image.open('hopper.jpg')
      a = np.asarray(im)

    Then this can be used to convert it to a Pillow image::

      im = Image.fromarray(a)

    :param obj: Object with array interface
    :param mode: Mode to use (will be determined from type if None)
      See: :ref:`concept-modes`.
    :returns: An image object.

    .. versionadded:: 1.1.6
    """
    arr = obj.__array_interface__
    shape = arr['shape']
    ndim = len(shape)
    strides = arr.get('strides', None)
    if mode is None:
        try:
            typekey = (1, 1) + shape[2:], arr['typestr']
            mode, rawmode = _fromarray_typemap[typekey]
        except KeyError:
            raise TypeError("Cannot handle this data type")
    else:
        rawmode = mode
    if mode in ["1", "L", "I", "P", "F"]:
        ndmax = 2
    elif mode == "RGB":
        ndmax = 3
    else:
        ndmax = 4
    if ndim > ndmax:
        raise ValueError("Too many dimensions: %d > %d." % (ndim, ndmax))

    size = shape[1], shape[0]
    if strides is not None:
        if hasattr(obj, 'tobytes'):
            obj = obj.tobytes()
        else:
            obj = obj.tostring()

    return frombuffer(mode, size, obj, "raw", rawmode, 0, 1)


def fromqimage(im):
    """Creates an image instance from a QImage image"""
    from . import ImageQt
    if not ImageQt.qt_is_installed:
        raise ImportError("Qt bindings are not installed")
    return ImageQt.fromqimage(im)


def fromqpixmap(im):
    """Creates an image instance from a QPixmap image"""
    from . import ImageQt
    if not ImageQt.qt_is_installed:
        raise ImportError("Qt bindings are not installed")
    return ImageQt.fromqpixmap(im)


_fromarray_typemap = {
    # (shape, typestr) => mode, rawmode
    # first two members of shape are set to one
    ((1, 1), "|b1"): ("1", "1;8"),
    ((1, 1), "|u1"): ("L", "L"),
    ((1, 1), "|i1"): ("I", "I;8"),
    ((1, 1), "<u2"): ("I", "I;16"),
    ((1, 1), ">u2"): ("I", "I;16B"),
    ((1, 1), "<i2"): ("I", "I;16S"),
    ((1, 1), ">i2"): ("I", "I;16BS"),
    ((1, 1), "<u4"): ("I", "I;32"),
    ((1, 1), ">u4"): ("I", "I;32B"),
    ((1, 1), "<i4"): ("I", "I;32S"),
    ((1, 1), ">i4"): ("I", "I;32BS"),
    ((1, 1), "<f4"): ("F", "F;32F"),
    ((1, 1), ">f4"): ("F", "F;32BF"),
    ((1, 1), "<f8"): ("F", "F;64F"),
    ((1, 1), ">f8"): ("F", "F;64BF"),
    ((1, 1, 2), "|u1"): ("LA", "LA"),
    ((1, 1, 3), "|u1"): ("RGB", "RGB"),
    ((1, 1, 4), "|u1"): ("RGBA", "RGBA"),
    }

# shortcuts
_fromarray_typemap[((1, 1), _ENDIAN + "i4")] = ("I", "I")
_fromarray_typemap[((1, 1), _ENDIAN + "f4")] = ("F", "F")


def _decompression_bomb_check(size):
    if MAX_IMAGE_PIXELS is None:
        return

    pixels = size[0] * size[1]

    if pixels > 2 * MAX_IMAGE_PIXELS:
        raise DecompressionBombError(
            "Image size (%d pixels) exceeds limit of %d pixels, "
            "could be decompression bomb DOS attack." %
            (pixels, 2 * MAX_IMAGE_PIXELS))

    if pixels > MAX_IMAGE_PIXELS:
        warnings.warn(
            "Image size (%d pixels) exceeds limit of %d pixels, "
            "could be decompression bomb DOS attack." %
            (pixels, MAX_IMAGE_PIXELS),
            DecompressionBombWarning)


def open(fp, mode="r"):
    """
    Opens and identifies the given image file.

    This is a lazy operation; this function identifies the file, but
    the file remains open and the actual image data is not read from
    the file until you try to process the data (or call the
    :py:meth:`~PIL.Image.Image.load` method).  See
    :py:func:`~PIL.Image.new`. See :ref:`file-handling`.

    :param fp: A filename (string), pathlib.Path object or a file object.
       The file object must implement :py:meth:`~file.read`,
       :py:meth:`~file.seek`, and :py:meth:`~file.tell` methods,
       and be opened in binary mode.
    :param mode: The mode.  If given, this argument must be "r".
    :returns: An :py:class:`~PIL.Image.Image` object.
    :exception IOError: If the file cannot be found, or the image cannot be
       opened and identified.
    """

    if mode != "r":
        raise ValueError("bad mode %r" % mode)

    exclusive_fp = False
    filename = ""
    if isPath(fp):
        filename = fp
    elif HAS_PATHLIB and isinstance(fp, Path):
        filename = str(fp.resolve())

    if filename:
        fp = builtins.open(filename, "rb")
        exclusive_fp = True

    try:
        fp.seek(0)
    except (AttributeError, io.UnsupportedOperation):
        fp = io.BytesIO(fp.read())
        exclusive_fp = True

    prefix = fp.read(16)

    preinit()

    accept_warnings = []

    def _open_core(fp, filename, prefix):
        for i in ID:
            try:
                factory, accept = OPEN[i]
                result = not accept or accept(prefix)
                if type(result) in [str, bytes]:
                    accept_warnings.append(result)
                elif result:
                    fp.seek(0)
                    im = factory(fp, filename)
                    _decompression_bomb_check(im.size)
                    return im
            except (SyntaxError, IndexError, TypeError, struct.error):
                # Leave disabled by default, spams the logs with image
                # opening failures that are entirely expected.
                # logger.debug("", exc_info=True)
                continue
            except Exception:
                if exclusive_fp:
                    fp.close()
                raise
        return None

    im = _open_core(fp, filename, prefix)

    if im is None:
        if init():
            im = _open_core(fp, filename, prefix)

    if im:
        im._exclusive_fp = exclusive_fp
        return im

    if exclusive_fp:
        fp.close()
    for message in accept_warnings:
        warnings.warn(message)
    raise IOError("cannot identify image file %r"
                  % (filename if filename else fp))

#
# Image processing.


def alpha_composite(im1, im2):
    """
    Alpha composite im2 over im1.

    :param im1: The first image. Must have mode RGBA.
    :param im2: The second image.  Must have mode RGBA, and the same size as
       the first image.
    :returns: An :py:class:`~PIL.Image.Image` object.
    """

    im1.load()
    im2.load()
    return im1._new(core.alpha_composite(im1.im, im2.im))


def blend(im1, im2, alpha):
    """
    Creates a new image by interpolating between two input images, using
    a constant alpha.::

        out = image1 * (1.0 - alpha) + image2 * alpha

    :param im1: The first image.
    :param im2: The second image.  Must have the same mode and size as
       the first image.
    :param alpha: The interpolation alpha factor.  If alpha is 0.0, a
       copy of the first image is returned. If alpha is 1.0, a copy of
       the second image is returned. There are no restrictions on the
       alpha value. If necessary, the result is clipped to fit into
       the allowed output range.
    :returns: An :py:class:`~PIL.Image.Image` object.
    """

    im1.load()
    im2.load()
    return im1._new(core.blend(im1.im, im2.im, alpha))


def composite(image1, image2, mask):
    """
    Create composite image by blending images using a transparency mask.

    :param image1: The first image.
    :param image2: The second image.  Must have the same mode and
       size as the first image.
    :param mask: A mask image.  This image can have mode
       "1", "L", or "RGBA", and must have the same size as the
       other two images.
    """

    image = image2.copy()
    image.paste(image1, None, mask)
    return image


def eval(image, *args):
    """
    Applies the function (which should take one argument) to each pixel
    in the given image. If the image has more than one band, the same
    function is applied to each band. Note that the function is
    evaluated once for each possible pixel value, so you cannot use
    random components or other generators.

    :param image: The input image.
    :param function: A function object, taking one integer argument.
    :returns: An :py:class:`~PIL.Image.Image` object.
    """

    return image.point(args[0])


def merge(mode, bands):
    """
    Merge a set of single band images into a new multiband image.

    :param mode: The mode to use for the output image. See:
        :ref:`concept-modes`.
    :param bands: A sequence containing one single-band image for
        each band in the output image.  All bands must have the
        same size.
    :returns: An :py:class:`~PIL.Image.Image` object.
    """

    if getmodebands(mode) != len(bands) or "*" in mode:
        raise ValueError("wrong number of bands")
    for band in bands[1:]:
        if band.mode != getmodetype(mode):
            raise ValueError("mode mismatch")
        if band.size != bands[0].size:
            raise ValueError("size mismatch")
    for band in bands:
        band.load()
    return bands[0]._new(core.merge(mode, *[b.im for b in bands]))


# --------------------------------------------------------------------
# Plugin registry

def register_open(id, factory, accept=None):
    """
    Register an image file plugin.  This function should not be used
    in application code.

    :param id: An image format identifier.
    :param factory: An image file factory method.
    :param accept: An optional function that can be used to quickly
       reject images having another format.
    """
    id = id.upper()
    ID.append(id)
    OPEN[id] = factory, accept


def register_mime(id, mimetype):
    """
    Registers an image MIME type.  This function should not be used
    in application code.

    :param id: An image format identifier.
    :param mimetype: The image MIME type for this format.
    """
    MIME[id.upper()] = mimetype


def register_save(id, driver):
    """
    Registers an image save function.  This function should not be
    used in application code.

    :param id: An image format identifier.
    :param driver: A function to save images in this format.
    """
    SAVE[id.upper()] = driver


def register_save_all(id, driver):
    """
    Registers an image function to save all the frames
    of a multiframe format.  This function should not be
    used in application code.

    :param id: An image format identifier.
    :param driver: A function to save images in this format.
    """
    SAVE_ALL[id.upper()] = driver


def register_extension(id, extension):
    """
    Registers an image extension.  This function should not be
    used in application code.

    :param id: An image format identifier.
    :param extension: An extension used for this format.
    """
    EXTENSION[extension.lower()] = id.upper()


def register_extensions(id, extensions):
    """
    Registers image extensions.  This function should not be
    used in application code.

    :param id: An image format identifier.
    :param extensions: A list of extensions used for this format.
    """
    for extension in extensions:
        register_extension(id, extension)


def registered_extensions():
    """
    Returns a dictionary containing all file extensions belonging
    to registered plugins
    """
    if not EXTENSION:
        init()
    return EXTENSION


def register_decoder(name, decoder):
    """
    Registers an image decoder.  This function should not be
    used in application code.

    :param name: The name of the decoder
    :param decoder: A callable(mode, args) that returns an
                    ImageFile.PyDecoder object

    .. versionadded:: 4.1.0
    """
    DECODERS[name] = decoder


def register_encoder(name, encoder):
    """
    Registers an image encoder.  This function should not be
    used in application code.

    :param name: The name of the encoder
    :param encoder: A callable(mode, args) that returns an
                    ImageFile.PyEncoder object

    .. versionadded:: 4.1.0
    """
    ENCODERS[name] = encoder


# --------------------------------------------------------------------
# Simple display support.  User code may override this.

def _show(image, **options):
    # override me, as necessary
    _showxv(image, **options)


def _showxv(image, title=None, **options):
    from . import ImageShow
    ImageShow.show(image, title, **options)


# --------------------------------------------------------------------
# Effects

def effect_mandelbrot(size, extent, quality):
    """
    Generate a Mandelbrot set covering the given extent.

    :param size: The requested size in pixels, as a 2-tuple:
       (width, height).
    :param extent: The extent to cover, as a 4-tuple:
       (x0, y0, x1, y2).
    :param quality: Quality.
    """
    return Image()._new(core.effect_mandelbrot(size, extent, quality))


def effect_noise(size, sigma):
    """
    Generate Gaussian noise centered around 128.

    :param size: The requested size in pixels, as a 2-tuple:
       (width, height).
    :param sigma: Standard deviation of noise.
    """
    return Image()._new(core.effect_noise(size, sigma))


def linear_gradient(mode):
    """
    Generate 256x256 linear gradient from black to white, top to bottom.

    :param mode: Input mode.
    """
    return Image()._new(core.linear_gradient(mode))


def radial_gradient(mode):
    """
    Generate 256x256 radial gradient from black to white, centre to edge.

    :param mode: Input mode.
    """
    return Image()._new(core.radial_gradient(mode))


# --------------------------------------------------------------------
# Resources

def _apply_env_variables(env=None):
    if env is None:
        env = os.environ

    for var_name, setter in [
        ('PILLOW_ALIGNMENT', core.set_alignment),
        ('PILLOW_BLOCK_SIZE', core.set_block_size),
        ('PILLOW_BLOCKS_MAX', core.set_blocks_max),
    ]:
        if var_name not in env:
            continue

        var = env[var_name].lower()

        units = 1
        for postfix, mul in [('k', 1024), ('m', 1024*1024)]:
            if var.endswith(postfix):
                units = mul
                var = var[:-len(postfix)]

        try:
            var = int(var) * units
        except ValueError:
            warnings.warn("{0} is not int".format(var_name))
            continue

        try:
            setter(var)
        except ValueError as e:
            warnings.warn("{0}: {1}".format(var_name, e))


_apply_env_variables()
atexit.register(core.clear_cache)
