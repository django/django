

from django.template import EngineHandler
from django.test import SimpleTestCase


class AutoescapeSettingTest(SimpleTestCase):

    """ Test for autoescape setting for DjangoTemplates, #25469 """

    def test_autoescape_off(self):
        templates = [{'BACKEND': 'django.template.backends.django.DjangoTemplates',
                      'OPTIONS': {'autoescape': False}}]
        engines = EngineHandler(templates=templates)
        self.assertEqual(engines['django'].from_string('Hello, {{ name }}').render({'name': 'Bob & Jim'}),
                         'Hello, Bob & Jim')

    def test_autoescape_default(self):
        templates = [{'BACKEND': 'django.template.backends.django.DjangoTemplates'}]
        engines = EngineHandler(templates=templates)
        self.assertEqual(engines['django'].from_string('Hello, {{ name }}').render({'name': 'Bob & Jim'}),
                         'Hello, Bob &amp; Jim')
