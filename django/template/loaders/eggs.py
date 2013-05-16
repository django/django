# Wrapper for loading templates from eggs via pkg_resources.resource_string.
from __future__ import unicode_literals

try:
    from pkg_resources import resource_string
except ImportError:
    resource_string = None

from django.conf import settings
from django.template.base import TemplateDoesNotExist
from django.template.loader import BaseLoader
from django.utils import six

class Loader(BaseLoader):
    is_usable = resource_string is not None

    def load_template_source(self, template_name, template_dirs=None):
        """
        Loads templates from Python eggs via pkg_resource.resource_string.

        For every installed app, it tries to get the resource (app, template_name).
        """
        if resource_string is not None:
            pkg_name = 'templates/' + template_name
            for app in settings.INSTALLED_APPS:
                try:
                    resource = resource_string(app, pkg_name)
                except Exception:
                    continue
                if not six.PY3:
                    resource = resource.decode(settings.FILE_CHARSET)
                return (resource, 'egg:%s:%s' % (app, pkg_name))
        raise TemplateDoesNotExist(template_name)
