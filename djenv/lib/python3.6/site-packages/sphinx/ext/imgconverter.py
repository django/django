# -*- coding: utf-8 -*-
"""
    sphinx.ext.imgconverter
    ~~~~~~~~~~~~~~~~~~~~~~~

    Image converter extension for Sphinx

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import locale
import subprocess

from sphinx.errors import ExtensionError
from sphinx.locale import __
from sphinx.transforms.post_transforms.images import ImageConverter
from sphinx.util import logging
from sphinx.util.osutil import ENOENT, EPIPE, EINVAL

if False:
    # For type annotation
    from typing import Any, Dict  # NOQA
    from sphinx.application import Sphinx  # NOQA


logger = logging.getLogger(__name__)


class ImagemagickConverter(ImageConverter):
    conversion_rules = [
        ('image/svg+xml', 'image/png'),
        ('image/gif', 'image/png'),
        ('application/pdf', 'image/png'),
    ]

    def is_available(self):
        # type: () -> bool
        """Confirms the converter is available or not."""
        try:
            args = [self.config.image_converter, '-version']
            logger.debug('Invoking %r ...', args)
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except (OSError, IOError):
            logger.warning(__('convert command %r cannot be run.'
                              'check the image_converter setting'),
                           self.config.image_converter)
            return False

        try:
            stdout, stderr = p.communicate()
        except (OSError, IOError) as err:
            if err.errno not in (EPIPE, EINVAL):
                raise
            stdout, stderr = p.stdout.read(), p.stderr.read()
            p.wait()
        if p.returncode != 0:
            encoding = locale.getpreferredencoding()
            logger.warning(__('convert exited with error:\n'
                              '[stderr]\n%s\n[stdout]\n%s'),
                           stderr.decode(encoding), stdout.decode(encoding))
            return False

        return True

    def convert(self, _from, _to):
        # type: (unicode, unicode) -> bool
        """Converts the image to expected one."""
        try:
            # append an index 0 to source filename to pick up the first frame
            # (or first page) of image (ex. Animation GIF, PDF)
            _from += '[0]'

            args = ([self.config.image_converter] +
                    self.config.image_converter_args +
                    [_from, _to])
            logger.debug('Invoking %r ...', args)
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as err:
            if err.errno != ENOENT:  # No such file or directory
                raise
            logger.warning(__('convert command %r cannot be run.'
                              'check the image_converter setting'),
                           self.config.image_converter)
            return False

        try:
            stdout, stderr = p.communicate()
        except (OSError, IOError) as err:
            if err.errno not in (EPIPE, EINVAL):
                raise
            stdout, stderr = p.stdout.read(), p.stderr.read()
            p.wait()
        if p.returncode != 0:
            raise ExtensionError(__('convert exited with error:\n'
                                    '[stderr]\n%s\n[stdout]\n%s') %
                                 (stderr, stdout))

        return True


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_post_transform(ImagemagickConverter)
    app.add_config_value('image_converter', 'convert', 'env')
    app.add_config_value('image_converter_args', [], 'env')

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
