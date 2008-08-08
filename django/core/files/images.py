"""
Utility functions for handling images.

Requires PIL, as you might imagine.
"""

from PIL import ImageFile as PIL
from django.core.files import File

class ImageFile(File):
    """
    A mixin for use alongside django.core.files.base.File, which provides
    additional features for dealing with images.
    """
    def _get_width(self):
        return self._get_image_dimensions()[0]
    width = property(_get_width)

    def _get_height(self):
        return self._get_image_dimensions()[1]
    height = property(_get_height)

    def _get_image_dimensions(self):
        if not hasattr(self, '_dimensions_cache'):
            self._dimensions_cache = get_image_dimensions(self)
        return self._dimensions_cache

def get_image_dimensions(file_or_path):
    """Returns the (width, height) of an image, given an open file or a path."""
    p = PIL.Parser()
    if hasattr(file_or_path, 'read'):
        file = file_or_path
    else:
        file = open(file_or_path, 'rb')
    while 1:
        data = file.read(1024)
        if not data:
            break
        p.feed(data)
        if p.image:
            return p.image.size
    return None
