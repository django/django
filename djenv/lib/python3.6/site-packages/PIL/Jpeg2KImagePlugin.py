#
# The Python Imaging Library
# $Id$
#
# JPEG2000 file handling
#
# History:
# 2014-03-12 ajh  Created
#
# Copyright (c) 2014 Coriolis Systems Limited
# Copyright (c) 2014 Alastair Houghton
#
# See the README file for information on usage and redistribution.
#
from . import Image, ImageFile
import struct
import os
import io

__version__ = "0.1"


def _parse_codestream(fp):
    """Parse the JPEG 2000 codestream to extract the size and component
    count from the SIZ marker segment, returning a PIL (size, mode) tuple."""

    hdr = fp.read(2)
    lsiz = struct.unpack('>H', hdr)[0]
    siz = hdr + fp.read(lsiz - 2)
    lsiz, rsiz, xsiz, ysiz, xosiz, yosiz, xtsiz, ytsiz, \
        xtosiz, ytosiz, csiz \
        = struct.unpack_from('>HHIIIIIIIIH', siz)
    ssiz = [None]*csiz
    xrsiz = [None]*csiz
    yrsiz = [None]*csiz
    for i in range(csiz):
        ssiz[i], xrsiz[i], yrsiz[i] \
            = struct.unpack_from('>BBB', siz, 36 + 3 * i)

    size = (xsiz - xosiz, ysiz - yosiz)
    if csiz == 1:
        if (yrsiz[0] & 0x7f) > 8:
            mode = 'I;16'
        else:
            mode = 'L'
    elif csiz == 2:
        mode = 'LA'
    elif csiz == 3:
        mode = 'RGB'
    elif csiz == 4:
        mode = 'RGBA'
    else:
        mode = None

    return (size, mode)


def _parse_jp2_header(fp):
    """Parse the JP2 header box to extract size, component count and
    color space information, returning a PIL (size, mode) tuple."""

    # Find the JP2 header box
    header = None
    while True:
        lbox, tbox = struct.unpack('>I4s', fp.read(8))
        if lbox == 1:
            lbox = struct.unpack('>Q', fp.read(8))[0]
            hlen = 16
        else:
            hlen = 8

        if lbox < hlen:
            raise SyntaxError('Invalid JP2 header length')

        if tbox == b'jp2h':
            header = fp.read(lbox - hlen)
            break
        else:
            fp.seek(lbox - hlen, os.SEEK_CUR)

    if header is None:
        raise SyntaxError('could not find JP2 header')

    size = None
    mode = None
    bpc = None
    nc = None

    hio = io.BytesIO(header)
    while True:
        lbox, tbox = struct.unpack('>I4s', hio.read(8))
        if lbox == 1:
            lbox = struct.unpack('>Q', hio.read(8))[0]
            hlen = 16
        else:
            hlen = 8

        content = hio.read(lbox - hlen)

        if tbox == b'ihdr':
            height, width, nc, bpc, c, unkc, ipr \
                = struct.unpack('>IIHBBBB', content)
            size = (width, height)
            if unkc:
                if nc == 1 and (bpc & 0x7f) > 8:
                    mode = 'I;16'
                elif nc == 1:
                    mode = 'L'
                elif nc == 2:
                    mode = 'LA'
                elif nc == 3:
                    mode = 'RGB'
                elif nc == 4:
                    mode = 'RGBA'
                break
        elif tbox == b'colr':
            meth, prec, approx = struct.unpack_from('>BBB', content)
            if meth == 1:
                cs = struct.unpack_from('>I', content, 3)[0]
                if cs == 16:   # sRGB
                    if nc == 1 and (bpc & 0x7f) > 8:
                        mode = 'I;16'
                    elif nc == 1:
                        mode = 'L'
                    elif nc == 3:
                        mode = 'RGB'
                    elif nc == 4:
                        mode = 'RGBA'
                    break
                elif cs == 17:  # grayscale
                    if nc == 1 and (bpc & 0x7f) > 8:
                        mode = 'I;16'
                    elif nc == 1:
                        mode = 'L'
                    elif nc == 2:
                        mode = 'LA'
                    break
                elif cs == 18:  # sYCC
                    if nc == 3:
                        mode = 'RGB'
                    elif nc == 4:
                        mode = 'RGBA'
                    break

    if size is None or mode is None:
        raise SyntaxError("Malformed jp2 header")

    return (size, mode)

##
# Image plugin for JPEG2000 images.


class Jpeg2KImageFile(ImageFile.ImageFile):
    format = "JPEG2000"
    format_description = "JPEG 2000 (ISO 15444)"

    def _open(self):
        sig = self.fp.read(4)
        if sig == b'\xff\x4f\xff\x51':
            self.codec = "j2k"
            self._size, self.mode = _parse_codestream(self.fp)
        else:
            sig = sig + self.fp.read(8)

            if sig == b'\x00\x00\x00\x0cjP  \x0d\x0a\x87\x0a':
                self.codec = "jp2"
                self._size, self.mode = _parse_jp2_header(self.fp)
            else:
                raise SyntaxError('not a JPEG 2000 file')

        if self.size is None or self.mode is None:
            raise SyntaxError('unable to determine size/mode')

        self.reduce = 0
        self.layers = 0

        fd = -1
        length = -1

        try:
            fd = self.fp.fileno()
            length = os.fstat(fd).st_size
        except Exception:
            fd = -1
            try:
                pos = self.fp.tell()
                self.fp.seek(0, 2)
                length = self.fp.tell()
                self.fp.seek(pos, 0)
            except Exception:
                length = -1

        self.tile = [('jpeg2k', (0, 0) + self.size, 0,
                      (self.codec, self.reduce, self.layers, fd, length))]

    def load(self):
        if self.reduce:
            power = 1 << self.reduce
            adjust = power >> 1
            self._size = (int((self.size[0] + adjust) / power),
                          int((self.size[1] + adjust) / power))

        if self.tile:
            # Update the reduce and layers settings
            t = self.tile[0]
            t3 = (t[3][0], self.reduce, self.layers, t[3][3], t[3][4])
            self.tile = [(t[0], (0, 0) + self.size, t[2], t3)]

        return ImageFile.ImageFile.load(self)


def _accept(prefix):
    return (prefix[:4] == b'\xff\x4f\xff\x51' or
            prefix[:12] == b'\x00\x00\x00\x0cjP  \x0d\x0a\x87\x0a')


# ------------------------------------------------------------
# Save support

def _save(im, fp, filename):
    if filename.endswith('.j2k'):
        kind = 'j2k'
    else:
        kind = 'jp2'

    # Get the keyword arguments
    info = im.encoderinfo

    offset = info.get('offset', None)
    tile_offset = info.get('tile_offset', None)
    tile_size = info.get('tile_size', None)
    quality_mode = info.get('quality_mode', 'rates')
    quality_layers = info.get('quality_layers', None)
    if quality_layers is not None and not (
        isinstance(quality_layers, (list, tuple)) and
        all([isinstance(quality_layer, (int, float))
             for quality_layer in quality_layers])
    ):
        raise ValueError('quality_layers must be a sequence of numbers')

    num_resolutions = info.get('num_resolutions', 0)
    cblk_size = info.get('codeblock_size', None)
    precinct_size = info.get('precinct_size', None)
    irreversible = info.get('irreversible', False)
    progression = info.get('progression', 'LRCP')
    cinema_mode = info.get('cinema_mode', 'no')
    fd = -1

    if hasattr(fp, "fileno"):
        try:
            fd = fp.fileno()
        except Exception:
            fd = -1

    im.encoderconfig = (
        offset,
        tile_offset,
        tile_size,
        quality_mode,
        quality_layers,
        num_resolutions,
        cblk_size,
        precinct_size,
        irreversible,
        progression,
        cinema_mode,
        fd
    )

    ImageFile._save(im, fp, [('jpeg2k', (0, 0)+im.size, 0, kind)])

# ------------------------------------------------------------
# Registry stuff


Image.register_open(Jpeg2KImageFile.format, Jpeg2KImageFile, _accept)
Image.register_save(Jpeg2KImageFile.format, _save)

Image.register_extensions(Jpeg2KImageFile.format,
                          [".jp2", ".j2k", ".jpc", ".jpf", ".jpx", ".j2c"])

Image.register_mime(Jpeg2KImageFile.format, 'image/jp2')
Image.register_mime(Jpeg2KImageFile.format, 'image/jpx')
