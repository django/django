"""Image utility functions for Sphinx."""

from __future__ import annotations

import base64
from os import path
from typing import TYPE_CHECKING, NamedTuple, overload

import imagesize

if TYPE_CHECKING:
    from os import PathLike

try:
    from PIL import Image
except ImportError:
    Image = None

mime_suffixes = {
    '.gif': 'image/gif',
    '.jpg': 'image/jpeg',
    '.png': 'image/png',
    '.pdf': 'application/pdf',
    '.svg': 'image/svg+xml',
    '.svgz': 'image/svg+xml',
    '.ai': 'application/illustrator',
}
_suffix_from_mime = {v: k for k, v in reversed(mime_suffixes.items())}


class DataURI(NamedTuple):
    mimetype: str
    charset: str
    data: bytes


def get_image_size(filename: str) -> tuple[int, int] | None:
    try:
        size = imagesize.get(filename)
        if size[0] == -1:
            size = None
        elif isinstance(size[0], float) or isinstance(size[1], float):
            size = (int(size[0]), int(size[1]))

        if size is None and Image:  # fallback to Pillow
            with Image.open(filename) as im:
                size = im.size

        return size
    except Exception:
        return None


@overload
def guess_mimetype(filename: PathLike[str] | str, default: str) -> str:
    ...


@overload
def guess_mimetype(filename: PathLike[str] | str, default: None = None) -> str | None:
    ...


def guess_mimetype(
    filename: PathLike[str] | str = '',
    default: str | None = None,
) -> str | None:
    ext = path.splitext(filename)[1].lower()
    if ext in mime_suffixes:
        return mime_suffixes[ext]
    if path.exists(filename):
        try:
            imgtype = _image_type_from_file(filename)
        except ValueError:
            pass
        else:
            return 'image/' + imgtype
    return default


def get_image_extension(mimetype: str) -> str | None:
    return _suffix_from_mime.get(mimetype)


def parse_data_uri(uri: str) -> DataURI | None:
    if not uri.startswith('data:'):
        return None

    # data:[<MIME-type>][;charset=<encoding>][;base64],<data>
    mimetype = 'text/plain'
    charset = 'US-ASCII'

    properties, data = uri[5:].split(',', 1)
    for prop in properties.split(';'):
        if prop == 'base64':
            pass  # skip
        elif prop.startswith('charset='):
            charset = prop[8:]
        elif prop:
            mimetype = prop

    image_data = base64.b64decode(data)
    return DataURI(mimetype, charset, image_data)


def _image_type_from_file(filename: PathLike[str] | str) -> str:
    with open(filename, 'rb') as f:
        header = f.read(32)  # 32 bytes

    # Bitmap
    # https://en.wikipedia.org/wiki/BMP_file_format#Bitmap_file_header
    if header.startswith(b'BM'):
        return 'bmp'

    # GIF
    # https://en.wikipedia.org/wiki/GIF#File_format
    if header.startswith((b'GIF87a', b'GIF89a')):
        return 'gif'

    # JPEG data
    # https://en.wikipedia.org/wiki/JPEG_File_Interchange_Format#File_format_structure
    if header.startswith(b'\xFF\xD8'):
        return 'jpeg'

    # Portable Network Graphics
    # https://en.wikipedia.org/wiki/PNG#File_header
    if header.startswith(b'\x89PNG\r\n\x1A\n'):
        return 'png'

    # Scalable Vector Graphics
    # https://svgwg.org/svg2-draft/struct.html
    if b'<svg' in header.lower():
        return 'svg+xml'

    # TIFF
    # https://en.wikipedia.org/wiki/TIFF#Byte_order
    if header.startswith((b'MM', b'II')):
        return 'tiff'

    # WebP
    # https://en.wikipedia.org/wiki/WebP#Technology
    if header.startswith(b'RIFF') and header[8:12] == b'WEBP':
        return 'webp'

    msg = 'Could not detect image type!'
    raise ValueError(msg)
