# Wrapper for loading templates from "template" directories in installed app packages.

from django.conf.settings import INSTALLED_APPS, TEMPLATE_FILE_EXTENSION
from django.core.template import TemplateDoesNotExist
import os

# At compile time, cache the directories to search.
app_template_dirs = []
for app in INSTALLED_APPS:
    i = app.rfind('.')
    m, a = app[:i], app[i+1:]
    mod = getattr(__import__(m, '', '', [a]), a)
    template_dir = os.path.join(os.path.dirname(mod.__file__), 'templates')
    if os.path.isdir(template_dir):
        app_template_dirs.append(template_dir)

        
# It won't change, so convert it to a tuple to save memory.
app_template_dirs = tuple(app_template_dirs)

def load_template_source(template_name, template_dirs=None):
    for template_dir in app_template_dirs:
        filepath = os.path.join(template_dir, template_name) + TEMPLATE_FILE_EXTENSION
        try:
            return (open(filepath).read(), filepath)
        except IOError:
            pass
    raise TemplateDoesNotExist, template_name
load_template_source.is_usable = True
