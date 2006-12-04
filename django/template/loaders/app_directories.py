# Wrapper for loading templates from "template" directories in installed app packages.

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.template import TemplateDoesNotExist
import os

# At compile time, cache the directories to search.
app_template_dirs = []
for app in settings.INSTALLED_APPS:
    i = app.rfind('.')
    if i == -1:
        m, a = app, None
    else:
        m, a = app[:i], app[i+1:]
    try:
        if a is None:
            mod = __import__(m, {}, {}, [])
        else:
            mod = getattr(__import__(m, {}, {}, [a]), a)
    except ImportError, e:
        raise ImproperlyConfigured, 'ImportError %s: %s' % (app, e.args[0])
    template_dir = os.path.join(os.path.dirname(mod.__file__), 'templates')
    if os.path.isdir(template_dir):
        app_template_dirs.append(template_dir)

# It won't change, so convert it to a tuple to save memory.
app_template_dirs = tuple(app_template_dirs)

def get_template_sources(template_name, template_dirs=None):
    for template_dir in app_template_dirs:
        yield os.path.join(template_dir, template_name)

def load_template_source(template_name, template_dirs=None):
    for filepath in get_template_sources(template_name, template_dirs):
        try:
            return (open(filepath).read(), filepath)
        except IOError:
            pass
    raise TemplateDoesNotExist, template_name
load_template_source.is_usable = True
