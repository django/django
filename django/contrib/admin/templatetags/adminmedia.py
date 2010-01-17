from django.template import Library
from django.utils.encoding import iri_to_uri

register = Library()

def admin_media_prefix():
    """
    Returns the string contained in the setting ADMIN_MEDIA_PREFIX.
    """
    try:
        from django.conf import settings
    except ImportError:
        return ''
    return iri_to_uri(settings.ADMIN_MEDIA_PREFIX)
admin_media_prefix = register.simple_tag(admin_media_prefix)
