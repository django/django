from django.apps import apps
from django.template import Library

register = Library()

if apps.is_installed('django.contrib.staticfiles'):
    from django.contrib.staticfiles.templatetags.staticfiles import static
else:
    from django.templatetags.static import static

static = register.simple_tag(static)
