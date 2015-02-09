# Wrapper for loading templates from eggs via pkg_resources.resource_string.
from __future__ import unicode_literals

from django.apps import apps
from django.template.base import TemplateDoesNotExist
from django.utils import six

from .base import Loader as BaseLoader

try:
    from pkg_resources import resource_string
except ImportError:
    resource_string = None


class Loader(BaseLoader):
    is_usable = resource_string is not None

    def load_template_source(self, template_name, template_dirs=None):
        """
        Loads templates from Python eggs via pkg_resource.resource_string.

        For every installed app, it tries to get the resource (app, template_name).
        """
        if resource_string is not None:
            pkg_name = 'templates/' + template_name
            for app_config in apps.get_app_configs():
                try:
                    resource = resource_string(app_config.name, pkg_name)
                except Exception:
                    continue
                if six.PY2:
                    resource = resource.decode(self.engine.file_charset)
                return (resource, 'egg:%s:%s' % (app_config.name, pkg_name))
        raise TemplateDoesNotExist(template_name)
