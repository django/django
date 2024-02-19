"""Image converter extension for Sphinx"""

from __future__ import annotations

import subprocess
import sys
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, Any

import sphinx
from sphinx.errors import ExtensionError
from sphinx.locale import __
from sphinx.transforms.post_transforms.images import ImageConverter
from sphinx.util import logging

if TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)


class ImagemagickConverter(ImageConverter):
    conversion_rules = [
        ('image/svg+xml', 'image/png'),
        ('image/gif', 'image/png'),
        ('application/pdf', 'image/png'),
        ('application/illustrator', 'image/png'),
    ]

    def is_available(self) -> bool:
        """Confirms the converter is available or not."""
        try:
            args = [self.config.image_converter, '-version']
            logger.debug('Invoking %r ...', args)
            subprocess.run(args, capture_output=True, check=True)
            return True
        except OSError as exc:
            logger.warning(__(
                "Unable to run the image conversion command %r. "
                "'sphinx.ext.imgconverter' requires ImageMagick by default. "
                "Ensure it is installed, or set the 'image_converter' option "
                "to a custom conversion command.\n\n"
                "Traceback: %s",
            ), self.config.image_converter, exc)
            return False
        except CalledProcessError as exc:
            logger.warning(__('convert exited with error:\n'
                              '[stderr]\n%r\n[stdout]\n%r'),
                           exc.stderr, exc.stdout)
            return False

    def convert(self, _from: str, _to: str) -> bool:
        """Converts the image to expected one."""
        try:
            # append an index 0 to source filename to pick up the first frame
            # (or first page) of image (ex. Animation GIF, PDF)
            _from += '[0]'

            args = ([self.config.image_converter] +
                    self.config.image_converter_args +
                    [_from, _to])
            logger.debug('Invoking %r ...', args)
            subprocess.run(args, capture_output=True, check=True)
            return True
        except OSError:
            logger.warning(__('convert command %r cannot be run, '
                              'check the image_converter setting'),
                           self.config.image_converter)
            return False
        except CalledProcessError as exc:
            raise ExtensionError(__('convert exited with error:\n'
                                    '[stderr]\n%r\n[stdout]\n%r') %
                                 (exc.stderr, exc.stdout)) from exc


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_post_transform(ImagemagickConverter)
    if sys.platform == 'win32':
        # On Windows, we use Imagemagik v7 by default to avoid the trouble for
        # convert.exe bundled with Windows.
        app.add_config_value('image_converter', 'magick', 'env')
        app.add_config_value('image_converter_args', ['convert'], 'env')
    else:
        # On other platform, we use Imagemagick v6 by default.  Especially,
        # Debian/Ubuntu are still based of v6.  So we can't use "magick" command
        # for these platforms.
        app.add_config_value('image_converter', 'convert', 'env')
        app.add_config_value('image_converter_args', [], 'env')

    return {
        'version': sphinx.__display_version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
