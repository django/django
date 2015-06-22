from template_tests.test_response import test_processor_name

from django.template import RequestContext
from django.template.backends.django import DjangoTemplates
from django.test import RequestFactory, ignore_warnings
from django.utils.deprecation import RemovedInDjango110Warning

from .test_dummy import TemplateStringsTests


class DjangoTemplatesTests(TemplateStringsTests):

    engine_class = DjangoTemplates
    backend_name = 'django'

    def test_context_has_priority_over_template_context_processors(self):
        # See ticket #23789.
        engine = DjangoTemplates({
            'DIRS': [],
            'APP_DIRS': False,
            'NAME': 'django',
            'OPTIONS': {
                'context_processors': [test_processor_name],
            },
        })

        template = engine.from_string('{{ processors }}')
        request = RequestFactory().get('/')

        # Check that context processors run
        content = template.render({}, request)
        self.assertEqual(content, 'yes')

        # Check that context overrides context processors
        content = template.render({'processors': 'no'}, request)
        self.assertEqual(content, 'no')

    @ignore_warnings(category=RemovedInDjango110Warning)
    def test_request_context_conflicts_with_request(self):
        template = self.engine.from_string('hello')

        request = RequestFactory().get('/')
        request_context = RequestContext(request)
        # This doesn't raise an exception.
        template.render(request_context, request)

        other_request = RequestFactory().get('/')
        msg = ("render() was called with a RequestContext and a request "
               "argument which refer to different requests. Make sure "
               "that the context argument is a dict or at least that "
               "the two arguments refer to the same request.")
        with self.assertRaisesMessage(ValueError, msg):
            template.render(request_context, other_request)
