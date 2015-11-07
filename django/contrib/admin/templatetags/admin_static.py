from django.template import Library
from django.templatetags.static import static as _static

register = Library()


@register.simple_tag
def static(path):
    # Implementation has been moved to django.templatetags.static.
    # Deprecation should start in Django 2.0
    return _static(path)
