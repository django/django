"""
Utility functions for handling images.

Requires PIL, as you might imagine.
"""

import ImageFile

def get_image_dimensions(path):
    """Returns the (width, height) of an image at a given path."""
    p = ImageFile.Parser()
    fp = open(path, 'rb')
    while 1:
        data = fp.read(1024)
        if not data:
            break
        p.feed(data)
        if p.image:
            return p.image.size
            break
    fp.close()
    return None
