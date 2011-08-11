from django import template
from django.contrib.staticfiles.storage import staticfiles_storage

register = template.Library()


@register.simple_tag
def static(path):
    """
    A template tag that returns the URL to a file
    using staticfiles' storage backend
    """
    return staticfiles_storage.url(path)
