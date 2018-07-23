from urllib.parse import urlsplit

from django.templatetags.static import static
from django.utils.html import format_html


class Asset:
    def __init__(self, path):
        self.path = path

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.path == other.path

    def __str__(self):
        if urlsplit(self.path).netloc:
            return self.path  # Do not touch absolute URLs
        return static(self.path)


class CSS(Asset):
    def __str__(self):
        path = super().__str__()
        return format_html('<link href="{}" rel="stylesheet" type="text/css">', path)


class JS(Asset):
    def __str__(self):
        path = super().__str__()
        return format_html('<script src="{}"></script>', path)
