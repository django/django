from django import template
from django.templatetags.static import (
    do_static as _do_static, static as _static,
)

register = template.Library()


def static(path):
    # Implementation has been moved to django.templatetags.static.
    # Deprecation should start in Django 2.0
    return _static(path)


@register.tag('static')
def do_static(parser, token):
    # Implementation has been moved to django.templatetags.static.
    # Deprecation should start in Django 2.0
    return _do_static(parser, token)
