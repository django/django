# Since this package contains a "django" module, this is required on Python 2.
from __future__ import absolute_import

import sys

import jinja2

from django.conf import settings
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.utils import six
from django.utils.module_loading import import_string

from .base import BaseEngine
from .utils import csrf_input_lazy, csrf_token_lazy


class Jinja2(BaseEngine):

    app_dirname = 'jinja2'

    def __init__(self, params):
        params = params.copy()
        options = params.pop('OPTIONS').copy()
        super(Jinja2, self).__init__(params)

        environment = options.pop('environment', 'jinja2.Environment')
        environment_cls = import_string(environment)

        options.setdefault('autoescape', True)
        options.setdefault('loader', jinja2.FileSystemLoader(self.template_dirs))
        options.setdefault('auto_reload', settings.DEBUG)
        options.setdefault('undefined',
                           jinja2.DebugUndefined if settings.DEBUG else jinja2.Undefined)

        self.env = environment_cls(**options)

    def from_string(self, template_code):
        return Template(self.env.from_string(template_code))

    def get_template(self, template_name):
        try:
            return Template(self.env.get_template(template_name))
        except jinja2.TemplateNotFound as exc:
            six.reraise(TemplateDoesNotExist, TemplateDoesNotExist(exc.args),
                        sys.exc_info()[2])
        except jinja2.TemplateSyntaxError as exc:
            six.reraise(TemplateSyntaxError, TemplateSyntaxError(exc.args),
                        sys.exc_info()[2])


class Template(object):

    def __init__(self, template):
        self.template = template

    def render(self, context=None, request=None):
        if context is None:
            context = {}
        if request is not None:
            context['request'] = request
            context['csrf_input'] = csrf_input_lazy(request)
            context['csrf_token'] = csrf_token_lazy(request)
        return self.template.render(context)
