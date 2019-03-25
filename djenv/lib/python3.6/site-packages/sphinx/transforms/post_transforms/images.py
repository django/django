# -*- coding: utf-8 -*-
"""
    sphinx.transforms.post_transforms.images
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Docutils transforms used by Sphinx.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import os
from hashlib import sha1
from math import ceil

from docutils import nodes
from six import text_type

from sphinx.locale import __
from sphinx.transforms import SphinxTransform
from sphinx.util import epoch_to_rfc1123, rfc1123_to_epoch
from sphinx.util import logging, requests
from sphinx.util.images import guess_mimetype, get_image_extension, parse_data_uri
from sphinx.util.osutil import ensuredir, movefile

if False:
    # For type annotation
    from typing import Any, Dict, List, Tuple  # NOQA
    from sphinx.application import Sphinx  # NOQA


logger = logging.getLogger(__name__)

MAX_FILENAME_LEN = 32


class BaseImageConverter(SphinxTransform):
    def apply(self):
        # type: () -> None
        for node in self.document.traverse(nodes.image):
            if self.match(node):
                self.handle(node)

    def match(self, node):
        # type: (nodes.Node) -> bool
        return True

    def handle(self, node):
        # type: (nodes.Node) -> None
        pass

    @property
    def imagedir(self):
        # type: () -> unicode
        return os.path.join(self.app.doctreedir, 'images')


class ImageDownloader(BaseImageConverter):
    default_priority = 100

    def match(self, node):
        # type: (nodes.Node) -> bool
        if self.app.builder.supported_image_types == []:
            return False
        elif self.app.builder.supported_remote_images:
            return False
        else:
            return '://' in node['uri']

    def handle(self, node):
        # type: (nodes.Node) -> None
        try:
            basename = os.path.basename(node['uri'])
            if '?' in basename:
                basename = basename.split('?')[0]
            if basename == '' or len(basename) > MAX_FILENAME_LEN:
                filename, ext = os.path.splitext(node['uri'])
                basename = sha1(filename.encode("utf-8")).hexdigest() + ext

            dirname = node['uri'].replace('://', '/').translate({ord("?"): u"/",
                                                                 ord("&"): u"/"})
            if len(dirname) > MAX_FILENAME_LEN:
                dirname = sha1(dirname.encode('utf-8')).hexdigest()
            ensuredir(os.path.join(self.imagedir, dirname))
            path = os.path.join(self.imagedir, dirname, basename)

            headers = {}
            if os.path.exists(path):
                timestamp = ceil(os.stat(path).st_mtime)  # type: float
                headers['If-Modified-Since'] = epoch_to_rfc1123(timestamp)

            r = requests.get(node['uri'], headers=headers)
            if r.status_code >= 400:
                logger.warning(__('Could not fetch remote image: %s [%d]') %
                               (node['uri'], r.status_code))
            else:
                self.app.env.original_image_uri[path] = node['uri']

                if r.status_code == 200:
                    with open(path, 'wb') as f:
                        f.write(r.content)

                last_modified = r.headers.get('last-modified')
                if last_modified:
                    timestamp = rfc1123_to_epoch(last_modified)
                    os.utime(path, (timestamp, timestamp))

                mimetype = guess_mimetype(path, default='*')
                if mimetype != '*' and os.path.splitext(basename)[1] == '':
                    # append a suffix if URI does not contain suffix
                    ext = get_image_extension(mimetype)
                    newpath = os.path.join(self.imagedir, dirname, basename + ext)
                    movefile(path, newpath)
                    self.app.env.original_image_uri.pop(path)
                    self.app.env.original_image_uri[newpath] = node['uri']
                    path = newpath
                node['candidates'].pop('?')
                node['candidates'][mimetype] = path
                node['uri'] = path
                self.app.env.images.add_file(self.env.docname, path)
        except Exception as exc:
            logger.warning(__('Could not fetch remote image: %s [%s]') %
                           (node['uri'], text_type(exc)))


class DataURIExtractor(BaseImageConverter):
    default_priority = 150

    def match(self, node):
        # type: (nodes.Node) -> bool
        if self.app.builder.supported_remote_images == []:
            return False
        elif self.app.builder.supported_data_uri_images is True:
            return False
        else:
            return 'data:' in node['uri']

    def handle(self, node):
        # type: (nodes.Node) -> None
        image = parse_data_uri(node['uri'])
        ext = get_image_extension(image.mimetype)
        if ext is None:
            logger.warning(__('Unknown image format: %s...'), node['uri'][:32],
                           location=node)
            return

        ensuredir(os.path.join(self.imagedir, 'embeded'))
        digest = sha1(image.data).hexdigest()
        path = os.path.join(self.imagedir, 'embeded', digest + ext)
        self.app.env.original_image_uri[path] = node['uri']

        with open(path, 'wb') as f:
            f.write(image.data)

        node['candidates'].pop('?')
        node['candidates'][image.mimetype] = path
        node['uri'] = path
        self.app.env.images.add_file(self.env.docname, path)


def get_filename_for(filename, mimetype):
    # type: (unicode, unicode) -> unicode
    basename = os.path.basename(filename)
    return os.path.splitext(basename)[0] + get_image_extension(mimetype)


class ImageConverter(BaseImageConverter):
    """A base class for image converters.

    An image converter is kind of Docutils transform module.  It is used to
    convert image files which does not supported by builder to appropriate
    format for that builder.

    For example, :py:class:`LaTeX builder <.LaTeXBuilder>` supports PDF,
    PNG and JPEG as image formats.  However it does not support SVG images.
    For such case, to use image converters allows to embed these
    unsupported images into the document.  One of image converters;
    :ref:`sphinx.ext.imgconverter <sphinx.ext.imgconverter>` can convert
    a SVG image to PNG format using Imagemagick internally.

    There are three steps to make your custom image converter:

    1. Make a subclass of ``ImageConverter`` class
    2. Override ``conversion_rules``, ``is_available()`` and ``convert()``
    3. Register your image converter to Sphinx using
       :py:meth:`.Sphinx.add_post_transform`
    """
    default_priority = 200

    #: A conversion rules the image converter supports.
    #: It is represented as a list of pair of source image format (mimetype) and
    #: destination one::
    #:
    #:     conversion_rules = [
    #:         ('image/svg+xml', 'image/png'),
    #:         ('image/gif', 'image/png'),
    #:         ('application/pdf', 'image/png'),
    #:     ]
    conversion_rules = []  # type: List[Tuple[unicode, unicode]]

    def __init__(self, *args, **kwargs):
        # type: (Any, Any) -> None
        self.available = None   # type: bool
                                # the converter is available or not.
                                # Will be checked at first conversion
        BaseImageConverter.__init__(self, *args, **kwargs)  # type: ignore

    def match(self, node):
        # type: (nodes.Node) -> bool
        if self.available is None:
            self.available = self.is_available()

        if not self.available:
            return False
        elif set(node['candidates']) & set(self.app.builder.supported_image_types):
            # builder supports the image; no need to convert
            return False
        else:
            rule = self.get_conversion_rule(node)
            if rule:
                return True
            else:
                return False

    def get_conversion_rule(self, node):
        # type: (nodes.Node) -> Tuple[unicode, unicode]
        for candidate in self.guess_mimetypes(node):
            for supported in self.app.builder.supported_image_types:
                rule = (candidate, supported)
                if rule in self.conversion_rules:
                    return rule

        return None

    def is_available(self):
        # type: () -> bool
        """Return the image converter is available or not."""
        raise NotImplementedError()

    def guess_mimetypes(self, node):
        # type: (nodes.Node) -> List[unicode]
        if '?' in node['candidates']:
            return []
        elif '*' in node['candidates']:
            from sphinx.util.images import guess_mimetype
            return [guess_mimetype(node['uri'])]
        else:
            return node['candidates'].keys()

    def handle(self, node):
        # type: (nodes.Node) -> None
        _from, _to = self.get_conversion_rule(node)

        if _from in node['candidates']:
            srcpath = node['candidates'][_from]
        else:
            srcpath = node['candidates']['*']

        filename = get_filename_for(srcpath, _to)
        ensuredir(self.imagedir)
        destpath = os.path.join(self.imagedir, filename)

        abs_srcpath = os.path.join(self.app.srcdir, srcpath)
        if self.convert(abs_srcpath, destpath):
            if '*' in node['candidates']:
                node['candidates']['*'] = destpath
            else:
                node['candidates'][_to] = destpath
            node['uri'] = destpath

            self.env.original_image_uri[destpath] = srcpath
            self.env.images.add_file(self.env.docname, destpath)

    def convert(self, _from, _to):
        # type: (unicode, unicode) -> bool
        """Convert a image file to expected format.

        *_from* is a path for source image file, and *_to* is a path for
        destination file.
        """
        raise NotImplementedError()


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_post_transform(ImageDownloader)
    app.add_post_transform(DataURIExtractor)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
