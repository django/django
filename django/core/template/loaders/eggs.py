# Wrapper for loading templates from eggs via pkg_resources.resource_string.

try:
    from pkg_resources import resource_string
except ImportError:
    resource_string = None

from django.core.template import TemplateDoesNotExist
from django.conf.settings import INSTALLED_APPS, TEMPLATE_FILE_EXTENSION

def load_template_source(name, dirs=None):
    """
    Loads templates from Python eggs via pkg_resource.resource_string.

    For every installed app, it tries to get the resource (app, name).
    """
    if resource_string is not None:
        pkg_name = 'templates/' + name + TEMPLATE_FILE_EXTENSION
        for app in INSTALLED_APPS:
            try:
                return (resource_string(app, pkg_name), 'egg:%s:%s ' % (app, pkg_name)) 
            except:
                pass
    raise TemplateDoesNotExist, name
load_template_source.is_usable = resource_string is not None
