import warnings

from django.template import Library
from django.templatetags.static import static as _static
from django.utils.deprecation import RemovedInDjango30Warning

register = Library()


@register.simple_tag
def static(path):
    warnings.warn(
        '{% load admin_static %} is deprecated in favor of {% load static %}.',
        RemovedInDjango30Warning,
    )
    return _static(path)
