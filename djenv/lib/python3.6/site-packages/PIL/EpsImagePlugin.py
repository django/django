#
# The Python Imaging Library.
# $Id$
#
# EPS file handling
#
# History:
# 1995-09-01 fl   Created (0.1)
# 1996-05-18 fl   Don't choke on "atend" fields, Ghostscript interface (0.2)
# 1996-08-22 fl   Don't choke on floating point BoundingBox values
# 1996-08-23 fl   Handle files from Macintosh (0.3)
# 2001-02-17 fl   Use 're' instead of 'regex' (Python 2.1) (0.4)
# 2003-09-07 fl   Check gs.close status (from Federico Di Gregorio) (0.5)
# 2014-05-07 e    Handling of EPS with binary preview and fixed resolution
#                 resizing
#
# Copyright (c) 1997-2003 by Secret Labs AB.
# Copyright (c) 1995-2003 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

import re
import io
import os
import sys
from . import Image, ImageFile
from ._binary import i32le as i32

__version__ = "0.5"

#
# --------------------------------------------------------------------

split = re.compile(r"^%%([^:]*):[ \t]*(.*)[ \t]*$")
field = re.compile(r"^%[%!\w]([^:]*)[ \t]*$")

gs_windows_binary = None
if sys.platform.startswith('win'):
    import shutil
    if hasattr(shutil, 'which'):
        which = shutil.which
    else:
        # Python 2
        import distutils.spawn
        which = distutils.spawn.find_executable
    for binary in ('gswin32c', 'gswin64c', 'gs'):
        if which(binary) is not None:
            gs_windows_binary = binary
            break
    else:
        gs_windows_binary = False


def has_ghostscript():
    if gs_windows_binary:
        return True
    if not sys.platform.startswith('win'):
        import subprocess
        try:
            with open(os.devnull, 'wb') as devnull:
                subprocess.check_call(['gs', '--version'], stdout=devnull)
            return True
        except OSError:
            # No Ghostscript
            pass
    return False


def Ghostscript(tile, size, fp, scale=1):
    """Render an image using Ghostscript"""

    # Unpack decoder tile
    decoder, tile, offset, data = tile[0]
    length, bbox = data

    # Hack to support hi-res rendering
    scale = int(scale) or 1
    # orig_size = size
    # orig_bbox = bbox
    size = (size[0] * scale, size[1] * scale)
    # resolution is dependent on bbox and size
    res = (float((72.0 * size[0]) / (bbox[2]-bbox[0])),
           float((72.0 * size[1]) / (bbox[3]-bbox[1])))

    import subprocess
    import tempfile

    out_fd, outfile = tempfile.mkstemp()
    os.close(out_fd)

    infile_temp = None
    if hasattr(fp, 'name') and os.path.exists(fp.name):
        infile = fp.name
    else:
        in_fd, infile_temp = tempfile.mkstemp()
        os.close(in_fd)
        infile = infile_temp

        # Ignore length and offset!
        # Ghostscript can read it
        # Copy whole file to read in Ghostscript
        with open(infile_temp, 'wb') as f:
            # fetch length of fp
            fp.seek(0, 2)
            fsize = fp.tell()
            # ensure start position
            # go back
            fp.seek(0)
            lengthfile = fsize
            while lengthfile > 0:
                s = fp.read(min(lengthfile, 100*1024))
                if not s:
                    break
                lengthfile -= len(s)
                f.write(s)

    # Build Ghostscript command
    command = ["gs",
               "-q",                         # quiet mode
               "-g%dx%d" % size,             # set output geometry (pixels)
               "-r%fx%f" % res,              # set input DPI (dots per inch)
               "-dBATCH",                    # exit after processing
               "-dNOPAUSE",                  # don't pause between pages
               "-dSAFER",                    # safe mode
               "-sDEVICE=ppmraw",            # ppm driver
               "-sOutputFile=%s" % outfile,  # output file
               # adjust for image origin
               "-c", "%d %d translate" % (-bbox[0], -bbox[1]),
               "-f", infile,                 # input file
               # showpage (see https://bugs.ghostscript.com/show_bug.cgi?id=698272)
               "-c", "showpage",
               ]

    if gs_windows_binary is not None:
        if not gs_windows_binary:
            raise WindowsError('Unable to locate Ghostscript on paths')
        command[0] = gs_windows_binary

    # push data through Ghostscript
    try:
        with open(os.devnull, 'w+b') as devnull:
            startupinfo = None
            if sys.platform.startswith('win'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.check_call(command, stdin=devnull, stdout=devnull,
                                  startupinfo=startupinfo)
        im = Image.open(outfile)
        im.load()
    finally:
        try:
            os.unlink(outfile)
            if infile_temp:
                os.unlink(infile_temp)
        except OSError:
            pass

    return im.im.copy()


class PSFile(object):
    """
    Wrapper for bytesio object that treats either CR or LF as end of line.
    """
    def __init__(self, fp):
        self.fp = fp
        self.char = None

    def seek(self, offset, whence=0):
        self.char = None
        self.fp.seek(offset, whence)

    def readline(self):
        s = self.char or b""
        self.char = None

        c = self.fp.read(1)
        while c not in b"\r\n":
            s = s + c
            c = self.fp.read(1)

        self.char = self.fp.read(1)
        # line endings can be 1 or 2 of \r \n, in either order
        if self.char in b"\r\n":
            self.char = None

        return s.decode('latin-1')


def _accept(prefix):
    return prefix[:4] == b"%!PS" or \
           (len(prefix) >= 4 and i32(prefix) == 0xC6D3D0C5)

##
# Image plugin for Encapsulated Postscript.  This plugin supports only
# a few variants of this format.


class EpsImageFile(ImageFile.ImageFile):
    """EPS File Parser for the Python Imaging Library"""

    format = "EPS"
    format_description = "Encapsulated Postscript"

    mode_map = {1: "L", 2: "LAB", 3: "RGB", 4: "CMYK"}

    def _open(self):
        (length, offset) = self._find_offset(self.fp)

        # Rewrap the open file pointer in something that will
        # convert line endings and decode to latin-1.
        fp = PSFile(self.fp)

        # go to offset - start of "%!PS"
        fp.seek(offset)

        box = None

        self.mode = "RGB"
        self._size = 1, 1  # FIXME: huh?

        #
        # Load EPS header

        s_raw = fp.readline()
        s = s_raw.strip('\r\n')

        while s_raw:
            if s:
                if len(s) > 255:
                    raise SyntaxError("not an EPS file")

                try:
                    m = split.match(s)
                except re.error:
                    raise SyntaxError("not an EPS file")

                if m:
                    k, v = m.group(1, 2)
                    self.info[k] = v
                    if k == "BoundingBox":
                        try:
                            # Note: The DSC spec says that BoundingBox
                            # fields should be integers, but some drivers
                            # put floating point values there anyway.
                            box = [int(float(i)) for i in v.split()]
                            self._size = box[2] - box[0], box[3] - box[1]
                            self.tile = [("eps", (0, 0) + self.size, offset,
                                          (length, box))]
                        except Exception:
                            pass

                else:
                    m = field.match(s)
                    if m:
                        k = m.group(1)

                        if k == "EndComments":
                            break
                        if k[:8] == "PS-Adobe":
                            self.info[k[:8]] = k[9:]
                        else:
                            self.info[k] = ""
                    elif s[0] == '%':
                        # handle non-DSC Postscript comments that some
                        # tools mistakenly put in the Comments section
                        pass
                    else:
                        raise IOError("bad EPS header")

            s_raw = fp.readline()
            s = s_raw.strip('\r\n')

            if s and s[:1] != "%":
                break

        #
        # Scan for an "ImageData" descriptor

        while s[:1] == "%":

            if len(s) > 255:
                raise SyntaxError("not an EPS file")

            if s[:11] == "%ImageData:":
                # Encoded bitmapped image.
                x, y, bi, mo = s[11:].split(None, 7)[:4]

                if int(bi) != 8:
                    break
                try:
                    self.mode = self.mode_map[int(mo)]
                except ValueError:
                    break

                self._size = int(x), int(y)
                return

            s = fp.readline().strip('\r\n')
            if not s:
                break

        if not box:
            raise IOError("cannot determine EPS bounding box")

    def _find_offset(self, fp):

        s = fp.read(160)

        if s[:4] == b"%!PS":
            # for HEAD without binary preview
            fp.seek(0, 2)
            length = fp.tell()
            offset = 0
        elif i32(s[0:4]) == 0xC6D3D0C5:
            # FIX for: Some EPS file not handled correctly / issue #302
            # EPS can contain binary data
            # or start directly with latin coding
            # more info see:
            # https://web.archive.org/web/20160528181353/http://partners.adobe.com/public/developer/en/ps/5002.EPSF_Spec.pdf
            offset = i32(s[4:8])
            length = i32(s[8:12])
        else:
            raise SyntaxError("not an EPS file")

        return (length, offset)

    def load(self, scale=1):
        # Load EPS via Ghostscript
        if not self.tile:
            return
        self.im = Ghostscript(self.tile, self.size, self.fp, scale)
        self.mode = self.im.mode
        self._size = self.im.size
        self.tile = []

    def load_seek(self, *args, **kwargs):
        # we can't incrementally load, so force ImageFile.parser to
        # use our custom load method by defining this method.
        pass


#
# --------------------------------------------------------------------

def _save(im, fp, filename, eps=1):
    """EPS Writer for the Python Imaging Library."""

    #
    # make sure image data is available
    im.load()

    #
    # determine postscript image mode
    if im.mode == "L":
        operator = (8, 1, "image")
    elif im.mode == "RGB":
        operator = (8, 3, "false 3 colorimage")
    elif im.mode == "CMYK":
        operator = (8, 4, "false 4 colorimage")
    else:
        raise ValueError("image mode is not supported")

    base_fp = fp
    wrapped_fp = False
    if fp != sys.stdout:
        if sys.version_info.major > 2:
            fp = io.TextIOWrapper(fp, encoding='latin-1')
            wrapped_fp = True

    try:
        if eps:
            #
            # write EPS header
            fp.write("%!PS-Adobe-3.0 EPSF-3.0\n")
            fp.write("%%Creator: PIL 0.1 EpsEncode\n")
            # fp.write("%%CreationDate: %s"...)
            fp.write("%%%%BoundingBox: 0 0 %d %d\n" % im.size)
            fp.write("%%Pages: 1\n")
            fp.write("%%EndComments\n")
            fp.write("%%Page: 1 1\n")
            fp.write("%%ImageData: %d %d " % im.size)
            fp.write("%d %d 0 1 1 \"%s\"\n" % operator)

        #
        # image header
        fp.write("gsave\n")
        fp.write("10 dict begin\n")
        fp.write("/buf %d string def\n" % (im.size[0] * operator[1]))
        fp.write("%d %d scale\n" % im.size)
        fp.write("%d %d 8\n" % im.size)  # <= bits
        fp.write("[%d 0 0 -%d 0 %d]\n" % (im.size[0], im.size[1], im.size[1]))
        fp.write("{ currentfile buf readhexstring pop } bind\n")
        fp.write(operator[2] + "\n")
        if hasattr(fp, "flush"):
            fp.flush()

        ImageFile._save(im, base_fp, [("eps", (0, 0)+im.size, 0, None)])

        fp.write("\n%%%%EndBinary\n")
        fp.write("grestore end\n")
        if hasattr(fp, "flush"):
            fp.flush()
    finally:
        if wrapped_fp:
            fp.detach()

#
# --------------------------------------------------------------------


Image.register_open(EpsImageFile.format, EpsImageFile, _accept)

Image.register_save(EpsImageFile.format, _save)

Image.register_extensions(EpsImageFile.format, [".ps", ".eps"])

Image.register_mime(EpsImageFile.format, "application/postscript")
