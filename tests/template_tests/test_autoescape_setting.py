
from django.template import EngineHandler
from django.test import SimpleTestCase


class AutoescapeSettingTest(SimpleTestCase):
    " Test for autoescape setting for DjangoTemplates, #25469 "

    def test_autoescape_off(self):
        engines = EngineHandler(templates=[{
                  'BACKEND': 'django.template.backends.django.DjangoTemplates',
                  'OPTIONS': { 'autoescape': False } }])
        self.assertEqual(
            engines['django'].from_string("Hello, {{ name }}").render({ "name": "Bob & Jim" }),
            "Hello, Bob & Jim"
            )

    def test_autoescape_default(self):
        engines = EngineHandler(templates=[{
                    'BACKEND': 'django.template.backends.django.DjangoTemplates',
                  }])
        self.assertEqual(
            engines['django'].from_string("Hello, {{ name }}").render({ "name": "Bob & Jim" }),
            "Hello, Bob &amp; Jim"
            )