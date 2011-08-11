from django.conf import settings
from django.template import Library

register = Library()

if 'django.contrib.staticfiles' in settings.INSTALLED_APPS:
    from django.contrib.staticfiles.templatetags.staticfiles import static
else:
    from django.templatetags.static import static

static = register.simple_tag(static)
