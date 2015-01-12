from django.template.backends.django import DjangoTemplates
from django.test import RequestFactory

from template_tests.test_response import test_processor_name

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
