from freedom.apps import apps
from freedom.template import Library

register = Library()

if apps.is_installed('freedom.contrib.staticfiles'):
    from freedom.contrib.staticfiles.templatetags.staticfiles import static
else:
    from freedom.templatetags.static import static

static = register.simple_tag(static)
