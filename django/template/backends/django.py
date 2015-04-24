# Since this package contains a "django" module, this is required on Python 2.
from __future__ import absolute_import

import sys
import warnings

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.context import Context, RequestContext, make_context
from django.template.engine import Engine, _dirs_undefined
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning

from .base import BaseEngine


class DjangoTemplates(BaseEngine):

    app_dirname = 'templates'

    def __init__(self, params):
        params = params.copy()
        options = params.pop('OPTIONS').copy()
        options.setdefault('debug', settings.DEBUG)
        options.setdefault('file_charset', settings.FILE_CHARSET)
        super(DjangoTemplates, self).__init__(params)
        self.engine = Engine(self.dirs, self.app_dirs, **options)

    def from_string(self, template_code):
        return Template(self.engine.from_string(template_code), self)

    def get_template(self, template_name, dirs=_dirs_undefined):
        try:
            return Template(self.engine.get_template(template_name, dirs), self)
        except TemplateDoesNotExist as exc:
            reraise(exc, self)


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
        # In Django 2.0 the isinstance checks should be removed. If passing a
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
                RemovedInDjango20Warning, stacklevel=2)

        elif isinstance(context, Context):
            warnings.warn(
                "render() must be called with a dict, not a Context.",
                RemovedInDjango20Warning, stacklevel=2)

        else:
            context = make_context(context, request)

        try:
            return self.template.render(context)
        except TemplateDoesNotExist as exc:
            reraise(exc, self.backend)


def reraise(exc, backend):
    """
    Reraise TemplateDoesNotExist while maintaining template debug information.
    """
    new = exc.__class__(*exc.args, tried=exc.tried, backend=backend)
    if hasattr(exc, 'template_debug'):
        new.template_debug = exc.template_debug
    six.reraise(exc.__class__, new, sys.exc_info()[2])
