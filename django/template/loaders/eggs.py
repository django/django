# Wrapper for loading templates from eggs via pkg_resources.resource_string.
from __future__ import unicode_literals

import warnings

from django.apps import apps
from django.template import Origin, TemplateDoesNotExist
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning

from .base import Loader as BaseLoader

try:
    from pkg_resources import resource_string
except ImportError:
    resource_string = None

warnings.warn('The egg template loader is deprecated.', RemovedInDjango20Warning)


class EggOrigin(Origin):

    def __init__(self, app_name, pkg_name, *args, **kwargs):
        self.app_name = app_name
        self.pkg_name = pkg_name
        super(EggOrigin, self).__init__(*args, **kwargs)


class Loader(BaseLoader):

    def __init__(self, engine):
        if resource_string is None:
            raise RuntimeError("Setuptools must be installed to use the egg loader")
        super(Loader, self).__init__(engine)

    def get_contents(self, origin):
        try:
            source = resource_string(origin.app_name, origin.pkg_name)
        except Exception:
            raise TemplateDoesNotExist(origin)

        if six.PY2:
            source = source.decode(self.engine.file_charset)

        return source

    def get_template_sources(self, template_name):
        pkg_name = 'templates/' + template_name
        for app_config in apps.get_app_configs():
            yield EggOrigin(
                app_name=app_config.name,
                pkg_name=pkg_name,
                name="egg:%s:%s" % (app_config.name, pkg_name),
                template_name=template_name,
                loader=self,
            )

    def load_template_source(self, template_name, template_dirs=None):
        """
        Loads templates from Python eggs via pkg_resource.resource_string.

        For every installed app, it tries to get the resource (app, template_name).
        """
        warnings.warn(
            'The load_template_sources() method is deprecated. Use '
            'get_template() or get_contents() instead.',
            RemovedInDjango20Warning,
        )
        for origin in self.get_template_sources(template_name):
            try:
                return self.get_contents(origin), origin.name
            except TemplateDoesNotExist:
                pass
        raise TemplateDoesNotExist(template_name)
