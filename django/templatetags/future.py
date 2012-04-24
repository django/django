from django.template import Library
from django.template.defaulttags import url as default_url, ssi as default_ssi

register = Library()

@register.tag
def ssi(parser, token):
    # Used for deprecation path during 1.3/1.4, will be removed in 2.0
    return default_ssi(parser, token)

@register.tag
def url(parser, token):
    # Used for deprecation path during 1.3/1.4, will be removed in 2.0
    return default_url(parser, token)
