import os
import warnings
from collections import Counter, OrderedDict

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import lru_cache
from django.utils._os import upath
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.functional import cached_property
from django.utils.module_loading import import_string


class InvalidTemplateEngineError(ImproperlyConfigured):
    pass


class EngineHandler(object):
    def __init__(self, templates=None):
        """
        templates is an optional list of template engine definitions
        (structured like settings.TEMPLATES).
        """
        self._templates = templates
        self._engines = {}

    @cached_property
    def templates(self):
        if self._templates is None:
            self._templates = settings.TEMPLATES

        if not self._templates:
            warnings.warn(
                "You haven't defined a TEMPLATES setting. You must do so "
                "before upgrading to Django 2.0. Otherwise Django will be "
                "unable to load templates.", RemovedInDjango20Warning)
            self._templates = [
                {
                    'BACKEND': 'django.template.backends.django.DjangoTemplates',
                    'DIRS': settings.TEMPLATE_DIRS,
                    'OPTIONS': {
                        'allowed_include_roots': settings.ALLOWED_INCLUDE_ROOTS,
                        'context_processors': settings.TEMPLATE_CONTEXT_PROCESSORS,
                        'debug': settings.TEMPLATE_DEBUG,
                        'loaders': settings.TEMPLATE_LOADERS,
                        'string_if_invalid': settings.TEMPLATE_STRING_IF_INVALID,
                    },
                },
            ]

        templates = OrderedDict()
        backend_names = []
        for tpl in self._templates:
            tpl = tpl.copy()
            try:
                # This will raise an exception if 'BACKEND' doesn't exist or
                # isn't a string containing at least one dot.
                default_name = tpl['BACKEND'].rsplit('.', 2)[-2]
            except Exception:
                invalid_backend = tpl.get('BACKEND', '<not defined>')
                raise ImproperlyConfigured(
                    "Invalid BACKEND for a template engine: {}. Check "
                    "your TEMPLATES setting.".format(invalid_backend))

            tpl.setdefault('NAME', default_name)
            tpl.setdefault('DIRS', [])
            tpl.setdefault('APP_DIRS', False)
            tpl.setdefault('OPTIONS', {})

            templates[tpl['NAME']] = tpl
            backend_names.append(tpl['NAME'])

        counts = Counter(backend_names)
        duplicates = [alias for alias, count in counts.most_common() if count > 1]
        if duplicates:
            raise ImproperlyConfigured(
                "Template engine aliases aren't unique, duplicates: {}. "
                "Set a unique NAME for each engine in settings.TEMPLATES."
                .format(", ".join(duplicates)))

        return templates

    def __getitem__(self, alias):
        try:
            return self._engines[alias]
        except KeyError:
            try:
                params = self.templates[alias]
            except KeyError:
                raise InvalidTemplateEngineError(
                    "Could not find config for '{}' "
                    "in settings.TEMPLATES".format(alias))

            # If importing or initializing the backend raises an exception,
            # self._engines[alias] isn't set and this code may get executed
            # again, so we must preserve the original params. See #24265.
            params = params.copy()
            backend = params.pop('BACKEND')
            engine_cls = import_string(backend)
            engine = engine_cls(params)

            self._engines[alias] = engine
            return engine

    def __iter__(self):
        return iter(self.templates)

    def all(self):
        return [self[alias] for alias in self]


@lru_cache.lru_cache()
def get_app_template_dirs(dirname):
    """
    Return an iterable of paths of directories to load app templates from.

    dirname is the name of the subdirectory containing templates inside
    installed applications.
    """
    template_dirs = []
    for app_config in apps.get_app_configs():
        if not app_config.path:
            continue
        template_dir = os.path.join(app_config.path, dirname)
        if os.path.isdir(template_dir):
            template_dirs.append(upath(template_dir))
    # Immutable return value because it will be cached and shared by callers.
    return tuple(template_dirs)
