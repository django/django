"""
Utility functions for handling images.

Requires PIL, as you might imagine.
"""
import zlib

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
            close = self.closed
            self.open()
            self._dimensions_cache = get_image_dimensions(self, close=close)
        return self._dimensions_cache


def get_image_dimensions(file_or_path, close=False):
    """
    Returns the (width, height) of an image, given an open file or a path.  Set
    'close' to True to close the file at the end if it is initially in an open
    state.
    """
    # Try to import PIL in either of the two ways it can end up installed.
    try:
        from PIL import ImageFile as PILImageFile
    except ImportError:
        import ImageFile as PILImageFile

    p = PILImageFile.Parser()
    if hasattr(file_or_path, 'read'):
        file = file_or_path
        file_pos = file.tell()
        file.seek(0)
    else:
        file = open(file_or_path, 'rb')
        close = True
    try:
        # Most of the time PIL only needs a small chunk to parse the image and
        # get the dimensions, but with some TIFF files PIL needs to parse the
        # whole file.
        chunk_size = 1024
        while 1:
            data = file.read(chunk_size)
            if not data:
                break
            try:
                p.feed(data)
            except zlib.error as e:
                # ignore zlib complaining on truncated stream, just feed more
                # data to parser (ticket #19457).
                if e.args[0].startswith("Error -5"):
                    pass
                else:
                    raise
            if p.image:
                return p.image.size
            chunk_size = chunk_size*2
        return None
    finally:
        if close:
            file.close()
        else:
            file.seek(file_pos)
