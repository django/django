# Since this package contains a "django" module, this is required on Python 2.
from __future__ import absolute_import

import sys
import warnings
from importlib import import_module
from pkgutil import walk_packages

from django.apps import apps
from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.context import Context, RequestContext, make_context
from django.template.engine import Engine, _dirs_undefined
from django.template.library import InvalidTemplateLibrary
from django.utils import six
from django.utils.deprecation import RemovedInDjango110Warning

from .base import BaseEngine


class DjangoTemplates(BaseEngine):

    app_dirname = 'templates'

    def __init__(self, params):
        params = params.copy()
        options = params.pop('OPTIONS').copy()
        options.setdefault('debug', settings.DEBUG)
        options.setdefault('file_charset', settings.FILE_CHARSET)
        libraries = options.get('libraries', {})
        options['libraries'] = self.get_templatetag_libraries(libraries)
        super(DjangoTemplates, self).__init__(params)
        self.engine = Engine(self.dirs, self.app_dirs, **options)

    def from_string(self, template_code):
        return Template(self.engine.from_string(template_code), self)

    def get_template(self, template_name, dirs=_dirs_undefined):
        try:
            return Template(self.engine.get_template(template_name, dirs), self)
        except TemplateDoesNotExist as exc:
            reraise(exc, self)

    def get_templatetag_libraries(self, custom_libraries):
        """
        Return a collation of template tag libraries from installed
        applications and the supplied custom_libraries argument.
        """
        libraries = get_installed_libraries()
        libraries.update(custom_libraries)
        return libraries


class Template(object):

    def __init__(self, template, backend):
        self.template = template
        self.backend = backend

    @property
    def origin(self):
        return self.template.origin

    def render(self, context=None, request=None):
        # A deprecation path is required here to cover the following usage:
        # >>> from django.template import Context
        # >>> from django.template.loader import get_template
        # >>> template = get_template('hello.html')
        # >>> template.render(Context({'name': 'world'}))
        # In Django 1.7 get_template() returned a django.template.Template.
        # In Django 1.8 it returns a django.template.backends.django.Template.
        # In Django 1.10 the isinstance checks should be removed. If passing a
        # Context or a RequestContext works by accident, it won't be an issue
        # per se, but it won't be officially supported either.
        if isinstance(context, RequestContext):
            if request is not None and request is not context.request:
                raise ValueError(
                    "render() was called with a RequestContext and a request "
                    "argument which refer to different requests. Make sure "
                    "that the context argument is a dict or at least that "
                    "the two arguments refer to the same request.")
            warnings.warn(
                "render() must be called with a dict, not a RequestContext.",
                RemovedInDjango110Warning, stacklevel=2)

        elif isinstance(context, Context):
            warnings.warn(
                "render() must be called with a dict, not a Context.",
                RemovedInDjango110Warning, stacklevel=2)

        else:
            context = make_context(context, request)

        try:
            return self.template.render(context)
        except TemplateDoesNotExist as exc:
            reraise(exc, self.backend)


def copy_exception(exc, backend=None):
    """
    Create a new TemplateDoesNotExist. Preserve its declared attributes and
    template debug data but discard __traceback__, __context__, and __cause__
    to make this object suitable for keeping around (in a cache, for example).
    """
    backend = backend or exc.backend
    new = exc.__class__(*exc.args, tried=exc.tried, backend=backend, chain=exc.chain)
    if hasattr(exc, 'template_debug'):
        new.template_debug = exc.template_debug
    return new


def reraise(exc, backend):
    """
    Reraise TemplateDoesNotExist while maintaining template debug information.
    """
    new = copy_exception(exc, backend)
    six.reraise(exc.__class__, new, sys.exc_info()[2])


def get_installed_libraries():
    """
    Return the built-in template tag libraries and those from installed
    applications. Libraries are stored in a dictionary where keys are the
    individual module names, not the full module paths. Example:
    django.templatetags.i18n is stored as i18n.
    """
    libraries = {}
    candidates = ['django.templatetags']
    candidates.extend(
        '%s.templatetags' % app_config.name
        for app_config in apps.get_app_configs())

    for candidate in candidates:
        try:
            pkg = import_module(candidate)
        except ImportError:
            # No templatetags package defined. This is safe to ignore.
            continue

        if hasattr(pkg, '__path__'):
            for name in get_package_libraries(pkg):
                libraries[name[len(candidate) + 1:]] = name

    return libraries


def get_package_libraries(pkg):
    """
    Recursively yield template tag libraries defined in submodules of a
    package.
    """
    for entry in walk_packages(pkg.__path__, pkg.__name__ + '.'):
        try:
            module = import_module(entry[1])
        except ImportError as e:
            raise InvalidTemplateLibrary(
                "Invalid template library specified. ImportError raised when "
                "trying to load '%s': %s" % (entry[1], e)
            )

        if hasattr(module, 'register'):
            yield entry[1]
