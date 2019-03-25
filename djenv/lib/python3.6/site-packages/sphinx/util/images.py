# -*- coding: utf-8 -*-
"""
    sphinx.util.images
    ~~~~~~~~~~~~~~~~~~

    Image utility functions for Sphinx.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import absolute_import

import base64
import imghdr
import warnings
from collections import OrderedDict
from os import path
from typing import NamedTuple

import imagesize
from six import PY3, BytesIO, iteritems

from sphinx.deprecation import RemovedInSphinx30Warning

try:
    from PIL import Image        # check for the Python Imaging Library
except ImportError:
    try:
        import Image
    except ImportError:
        Image = None

if False:
    # For type annotation
    from typing import Dict, IO, List, Tuple  # NOQA

if PY3:
    unicode = str  # special alias for static typing...

mime_suffixes = OrderedDict([
    ('.gif', 'image/gif'),
    ('.jpg', 'image/jpeg'),
    ('.png', 'image/png'),
    ('.pdf', 'application/pdf'),
    ('.svg', 'image/svg+xml'),
    ('.svgz', 'image/svg+xml'),
])  # type: Dict[unicode, unicode]

DataURI = NamedTuple('DataURI', [('mimetype', unicode),
                                 ('charset', unicode),
                                 ('data', bytes)])


def get_image_size(filename):
    # type: (unicode) -> Tuple[int, int]
    try:
        size = imagesize.get(filename)
        if size[0] == -1:
            size = None

        if size is None and Image:  # fallback to PIL
            im = Image.open(filename)
            size = im.size
            try:
                im.fp.close()
            except Exception:
                pass

        return size
    except Exception:
        return None


def guess_mimetype_for_stream(stream, default=None):
    # type: (IO, unicode) -> unicode
    imgtype = imghdr.what(stream)  # type: ignore
    if imgtype:
        return 'image/' + imgtype
    else:
        return default


def guess_mimetype(filename='', content=None, default=None):
    # type: (unicode, unicode, unicode) -> unicode
    _, ext = path.splitext(filename.lower())
    if ext in mime_suffixes:
        return mime_suffixes[ext]
    elif content:
        warnings.warn('The content argument of guess_mimetype() is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)
        return guess_mimetype_for_stream(BytesIO(content), default=default)
    elif path.exists(filename):
        with open(filename, 'rb') as f:
            return guess_mimetype_for_stream(f, default=default)

    return default


def get_image_extension(mimetype):
    # type: (unicode) -> unicode
    for ext, _mimetype in iteritems(mime_suffixes):
        if mimetype == _mimetype:
            return ext

    return None


def parse_data_uri(uri):
    # type: (unicode) -> DataURI
    if not uri.startswith('data:'):
        return None

    # data:[<MIME-type>][;charset=<encoding>][;base64],<data>
    mimetype = u'text/plain'
    charset = u'US-ASCII'

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


def test_svg(h, f):
    # type: (unicode, IO) -> unicode
    """An additional imghdr library helper; test the header is SVG's or not."""
    try:
        if '<svg' in h.decode('utf-8').lower():
            return 'svg+xml'
    except UnicodeDecodeError:
        pass

    return None


# install test_svg() to imghdr
# refs: https://docs.python.org/3.6/library/imghdr.html#imghdr.tests
imghdr.tests.append(test_svg)  # type: ignore
