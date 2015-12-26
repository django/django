from django.template import Library
from django.templatetags.static import static as _static

register = Library()


@register.simple_tag
def static(path):
    # Backwards compatibility alias for django.templatetags.static.static().
    # Deprecation should start in Django 2.0.
    return _static(path)
