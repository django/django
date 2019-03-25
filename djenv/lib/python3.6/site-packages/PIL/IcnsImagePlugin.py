#
# The Python Imaging Library.
# $Id$
#
# macOS icns file decoder, based on icns.py by Bob Ippolito.
#
# history:
# 2004-10-09 fl   Turned into a PIL plugin; removed 2.3 dependencies.
#
# Copyright (c) 2004 by Bob Ippolito.
# Copyright (c) 2004 by Secret Labs.
# Copyright (c) 2004 by Fredrik Lundh.
# Copyright (c) 2014 by Alastair Houghton.
#
# See the README file for information on usage and redistribution.
#

from PIL import Image, ImageFile, PngImagePlugin
from PIL._binary import i8
import io
import os
import shutil
import struct
import sys
import tempfile

enable_jpeg2k = hasattr(Image.core, 'jp2klib_version')
if enable_jpeg2k:
    from PIL import Jpeg2KImagePlugin

HEADERSIZE = 8


def nextheader(fobj):
    return struct.unpack('>4sI', fobj.read(HEADERSIZE))


def read_32t(fobj, start_length, size):
    # The 128x128 icon seems to have an extra header for some reason.
    (start, length) = start_length
    fobj.seek(start)
    sig = fobj.read(4)
    if sig != b'\x00\x00\x00\x00':
        raise SyntaxError('Unknown signature, expecting 0x00000000')
    return read_32(fobj, (start + 4, length - 4), size)


def read_32(fobj, start_length, size):
    """
    Read a 32bit RGB icon resource.  Seems to be either uncompressed or
    an RLE packbits-like scheme.
    """
    (start, length) = start_length
    fobj.seek(start)
    pixel_size = (size[0] * size[2], size[1] * size[2])
    sizesq = pixel_size[0] * pixel_size[1]
    if length == sizesq * 3:
        # uncompressed ("RGBRGBGB")
        indata = fobj.read(length)
        im = Image.frombuffer("RGB", pixel_size, indata, "raw", "RGB", 0, 1)
    else:
        # decode image
        im = Image.new("RGB", pixel_size, None)
        for band_ix in range(3):
            data = []
            bytesleft = sizesq
            while bytesleft > 0:
                byte = fobj.read(1)
                if not byte:
                    break
                byte = i8(byte)
                if byte & 0x80:
                    blocksize = byte - 125
                    byte = fobj.read(1)
                    for i in range(blocksize):
                        data.append(byte)
                else:
                    blocksize = byte + 1
                    data.append(fobj.read(blocksize))
                bytesleft -= blocksize
                if bytesleft <= 0:
                    break
            if bytesleft != 0:
                raise SyntaxError(
                    "Error reading channel [%r left]" % bytesleft
                    )
            band = Image.frombuffer(
                "L", pixel_size, b"".join(data), "raw", "L", 0, 1
                )
            im.im.putband(band.im, band_ix)
    return {"RGB": im}


def read_mk(fobj, start_length, size):
    # Alpha masks seem to be uncompressed
    start = start_length[0]
    fobj.seek(start)
    pixel_size = (size[0] * size[2], size[1] * size[2])
    sizesq = pixel_size[0] * pixel_size[1]
    band = Image.frombuffer(
        "L", pixel_size, fobj.read(sizesq), "raw", "L", 0, 1
        )
    return {"A": band}


def read_png_or_jpeg2000(fobj, start_length, size):
    (start, length) = start_length
    fobj.seek(start)
    sig = fobj.read(12)
    if sig[:8] == b'\x89PNG\x0d\x0a\x1a\x0a':
        fobj.seek(start)
        im = PngImagePlugin.PngImageFile(fobj)
        return {"RGBA": im}
    elif sig[:4] == b'\xff\x4f\xff\x51' \
            or sig[:4] == b'\x0d\x0a\x87\x0a' \
            or sig == b'\x00\x00\x00\x0cjP  \x0d\x0a\x87\x0a':
        if not enable_jpeg2k:
            raise ValueError('Unsupported icon subimage format (rebuild PIL '
                             'with JPEG 2000 support to fix this)')
        # j2k, jpc or j2c
        fobj.seek(start)
        jp2kstream = fobj.read(length)
        f = io.BytesIO(jp2kstream)
        im = Jpeg2KImagePlugin.Jpeg2KImageFile(f)
        if im.mode != 'RGBA':
            im = im.convert('RGBA')
        return {"RGBA": im}
    else:
        raise ValueError('Unsupported icon subimage format')


class IcnsFile(object):

    SIZES = {
        (512, 512, 2): [
            (b'ic10', read_png_or_jpeg2000),
        ],
        (512, 512, 1): [
            (b'ic09', read_png_or_jpeg2000),
        ],
        (256, 256, 2): [
            (b'ic14', read_png_or_jpeg2000),
        ],
        (256, 256, 1): [
            (b'ic08', read_png_or_jpeg2000),
        ],
        (128, 128, 2): [
            (b'ic13', read_png_or_jpeg2000),
        ],
        (128, 128, 1): [
            (b'ic07', read_png_or_jpeg2000),
            (b'it32', read_32t),
            (b't8mk', read_mk),
        ],
        (64, 64, 1): [
            (b'icp6', read_png_or_jpeg2000),
        ],
        (32, 32, 2): [
            (b'ic12', read_png_or_jpeg2000),
        ],
        (48, 48, 1): [
            (b'ih32', read_32),
            (b'h8mk', read_mk),
        ],
        (32, 32, 1): [
            (b'icp5', read_png_or_jpeg2000),
            (b'il32', read_32),
            (b'l8mk', read_mk),
        ],
        (16, 16, 2): [
            (b'ic11', read_png_or_jpeg2000),
        ],
        (16, 16, 1): [
            (b'icp4', read_png_or_jpeg2000),
            (b'is32', read_32),
            (b's8mk', read_mk),
        ],
    }

    def __init__(self, fobj):
        """
        fobj is a file-like object as an icns resource
        """
        # signature : (start, length)
        self.dct = dct = {}
        self.fobj = fobj
        sig, filesize = nextheader(fobj)
        if sig != b'icns':
            raise SyntaxError('not an icns file')
        i = HEADERSIZE
        while i < filesize:
            sig, blocksize = nextheader(fobj)
            if blocksize <= 0:
                raise SyntaxError('invalid block header')
            i += HEADERSIZE
            blocksize -= HEADERSIZE
            dct[sig] = (i, blocksize)
            fobj.seek(blocksize, 1)
            i += blocksize

    def itersizes(self):
        sizes = []
        for size, fmts in self.SIZES.items():
            for (fmt, reader) in fmts:
                if fmt in self.dct:
                    sizes.append(size)
                    break
        return sizes

    def bestsize(self):
        sizes = self.itersizes()
        if not sizes:
            raise SyntaxError("No 32bit icon resources found")
        return max(sizes)

    def dataforsize(self, size):
        """
        Get an icon resource as {channel: array}.  Note that
        the arrays are bottom-up like windows bitmaps and will likely
        need to be flipped or transposed in some way.
        """
        dct = {}
        for code, reader in self.SIZES[size]:
            desc = self.dct.get(code)
            if desc is not None:
                dct.update(reader(self.fobj, desc, size))
        return dct

    def getimage(self, size=None):
        if size is None:
            size = self.bestsize()
        if len(size) == 2:
            size = (size[0], size[1], 1)
        channels = self.dataforsize(size)

        im = channels.get('RGBA', None)
        if im:
            return im

        im = channels.get("RGB").copy()
        try:
            im.putalpha(channels["A"])
        except KeyError:
            pass
        return im


##
# Image plugin for Mac OS icons.

class IcnsImageFile(ImageFile.ImageFile):
    """
    PIL image support for Mac OS .icns files.
    Chooses the best resolution, but will possibly load
    a different size image if you mutate the size attribute
    before calling 'load'.

    The info dictionary has a key 'sizes' that is a list
    of sizes that the icns file has.
    """

    format = "ICNS"
    format_description = "Mac OS icns resource"

    def _open(self):
        self.icns = IcnsFile(self.fp)
        self.mode = 'RGBA'
        self.info['sizes'] = self.icns.itersizes()
        self.best_size = self.icns.bestsize()
        self.size = (self.best_size[0] * self.best_size[2],
                     self.best_size[1] * self.best_size[2])
        # Just use this to see if it's loaded or not yet.
        self.tile = ('',)

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        info_size = value
        if info_size not in self.info['sizes'] and len(info_size) == 2:
            info_size = (info_size[0], info_size[1], 1)
        if info_size not in self.info['sizes'] and len(info_size) == 3 and \
           info_size[2] == 1:
            simple_sizes = [(size[0] * size[2], size[1] * size[2])
                            for size in self.info['sizes']]
            if value in simple_sizes:
                info_size = self.info['sizes'][simple_sizes.index(value)]
        if info_size not in self.info['sizes']:
            raise ValueError(
                "This is not one of the allowed sizes of this image")
        self._size = value

    def load(self):
        if len(self.size) == 3:
            self.best_size = self.size
            self.size = (self.best_size[0] * self.best_size[2],
                         self.best_size[1] * self.best_size[2])

        Image.Image.load(self)
        if not self.tile:
            return
        self.load_prepare()
        # This is likely NOT the best way to do it, but whatever.
        im = self.icns.getimage(self.best_size)

        # If this is a PNG or JPEG 2000, it won't be loaded yet
        im.load()

        self.im = im.im
        self.mode = im.mode
        self.size = im.size
        if self._exclusive_fp:
            self.fp.close()
        self.fp = None
        self.icns = None
        self.tile = ()
        self.load_end()


def _save(im, fp, filename):
    """
    Saves the image as a series of PNG files,
    that are then converted to a .icns file
    using the macOS command line utility 'iconutil'.

    macOS only.
    """
    if hasattr(fp, "flush"):
        fp.flush()

    # create the temporary set of pngs
    iconset = tempfile.mkdtemp('.iconset')
    provided_images = {im.width: im
                       for im in im.encoderinfo.get("append_images", [])}
    last_w = None
    second_path = None
    for w in [16, 32, 128, 256, 512]:
        prefix = 'icon_{}x{}'.format(w, w)

        first_path = os.path.join(iconset, prefix+'.png')
        if last_w == w:
            shutil.copyfile(second_path, first_path)
        else:
            im_w = provided_images.get(w, im.resize((w, w), Image.LANCZOS))
            im_w.save(first_path)

        second_path = os.path.join(iconset, prefix+'@2x.png')
        im_w2 = provided_images.get(w*2, im.resize((w*2, w*2), Image.LANCZOS))
        im_w2.save(second_path)
        last_w = w*2

    # iconutil -c icns -o {} {}
    from subprocess import Popen, PIPE, CalledProcessError

    convert_cmd = ["iconutil", "-c", "icns", "-o", filename, iconset]
    with open(os.devnull, 'wb') as devnull:
        convert_proc = Popen(convert_cmd, stdout=PIPE, stderr=devnull)

    convert_proc.stdout.close()

    retcode = convert_proc.wait()

    # remove the temporary files
    shutil.rmtree(iconset)

    if retcode:
        raise CalledProcessError(retcode, convert_cmd)


Image.register_open(IcnsImageFile.format, IcnsImageFile,
                    lambda x: x[:4] == b'icns')
Image.register_extension(IcnsImageFile.format, '.icns')

if sys.platform == 'darwin':
    Image.register_save(IcnsImageFile.format, _save)

    Image.register_mime(IcnsImageFile.format, "image/icns")


if __name__ == '__main__':

    if len(sys.argv) < 2:
        print("Syntax: python IcnsImagePlugin.py [file]")
        sys.exit()

    imf = IcnsImageFile(open(sys.argv[1], 'rb'))
    for size in imf.info['sizes']:
        imf.size = size
        imf.load()
        im = imf.im
        im.save('out-%s-%s-%s.png' % size)
    im = Image.open(sys.argv[1])
    im.save("out.png")
    if sys.platform == 'windows':
        os.startfile("out.png")
