# Since this package contains a "django" module, this is required on Python 2.
from __future__ import absolute_import

from django.conf import settings
from django.template.context import Context, RequestContext
from django.template.engine import Engine


from .base import BaseEngine


class DjangoTemplates(BaseEngine):

    app_dirname = 'templates'

    def __init__(self, params):
        params = params.copy()
        options = params.pop('OPTIONS').copy()
        options.setdefault('debug', settings.TEMPLATE_DEBUG)
        options.setdefault('file_charset', settings.FILE_CHARSET)
        super(DjangoTemplates, self).__init__(params)
        self.engine = Engine(self.dirs, self.app_dirs, **options)

    def from_string(self, template_code):
        return Template(self.engine.from_string(template_code))

    def get_template(self, template_name):
        return Template(self.engine.get_template(template_name))


class Template(object):

    def __init__(self, template):
        self.template = template

    def render(self, context=None, request=None):
        if request is None:
            context = Context(context)
        else:
            context = RequestContext(request, context)
        return self.template.render(context)
