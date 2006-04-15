# Wrapper for loading templates from eggs via pkg_resources.resource_string.

try:
    from pkg_resources import resource_string
except ImportError:
    resource_string = None

from django.template import TemplateDoesNotExist
from django.conf import settings

def load_template_source(template_name, template_dirs=None):
    """
    Loads templates from Python eggs via pkg_resource.resource_string.

    For every installed app, it tries to get the resource (app, template_name).
    """
    if resource_string is not None:
        pkg_name = 'templates/' + template_name
        for app in settings.INSTALLED_APPS:
            try:
                return (resource_string(app, pkg_name), 'egg:%s:%s ' % (app, pkg_name))
            except:
                pass
    raise TemplateDoesNotExist, template_name
load_template_source.is_usable = resource_string is not None
