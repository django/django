import re

def get_thumbnail_url(photo_url, width):
    bits = photo_url.split('/')
    bits[-1] = re.sub(r'(?i)\.(gif|jpg)$', '_t%s.\\1' % width, bits[-1])
    return '/'.join(bits)
