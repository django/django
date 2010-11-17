from django.template import Library
from django.templatetags.static import PrefixNode

register = Library()

@register.simple_tag
def admin_media_prefix():
    """
    Returns the string contained in the setting ADMIN_MEDIA_PREFIX.
    """
    return PrefixNode.handle_simple("ADMIN_MEDIA_PREFIX")
