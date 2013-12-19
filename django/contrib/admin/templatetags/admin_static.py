from django.core.apps import app_cache
from django.template import Library

register = Library()

if app_cache.has_app('django.contrib.staticfiles'):
    from django.contrib.staticfiles.templatetags.staticfiles import static
else:
    from django.templatetags.static import static

static = register.simple_tag(static)
