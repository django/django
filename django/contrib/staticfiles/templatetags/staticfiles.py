import warnings

from django import template
from django.templatetags.static import (
    do_static as _do_static, static as _static,
)
from django.utils.deprecation import RemovedInDjango30Warning

register = template.Library()


def static(path):
    warnings.warn(
        'django.contrib.staticfiles.templatetags.static() is deprecated in '
        'favor of django.templatetags.static.static().',
        RemovedInDjango30Warning,
        stacklevel=2,
    )
    return _static(path)


@register.tag('static')
def do_static(parser, token):
    warnings.warn(
        '{% load staticfiles %} is deprecated in favor of {% load static %}.',
        RemovedInDjango30Warning,
    )
    return _do_static(parser, token)
