import warnings

from django.template import Library
from django.template import defaulttags
from django.utils.deprecation import (RemovedInDjango19Warning,
    RemovedInDjango18Warning)

register = Library()


@register.tag
def ssi(parser, token):
    warnings.warn(
        "Loading the `ssi` tag from the `future` library is deprecated and "
        "will be removed in Django 1.9. Use the default `ssi` tag instead.",
        RemovedInDjango19Warning)
    return defaulttags.ssi(parser, token)


@register.tag
def url(parser, token):
    warnings.warn(
        "Loading the `url` tag from the `future` library is deprecated and "
        "will be removed in Django 1.9. Use the default `url` tag instead.",
        RemovedInDjango19Warning)
    return defaulttags.url(parser, token)


@register.tag
def cycle(parser, token):
    warnings.warn(
        "Loading the `cycle` tag from the `future` library is deprecated and "
        "will be removed in Django 1.8. Use the default `cycle` tag instead.",
        RemovedInDjango18Warning)
    return defaulttags.cycle(parser, token)


@register.tag
def firstof(parser, token):
    warnings.warn(
        "Loading the `firstof` tag from the `future` library is deprecated and "
        "will be removed in Django 1.8. Use the default `firstof` tag instead.",
        RemovedInDjango18Warning)
    return defaulttags.firstof(parser, token)
