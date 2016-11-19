from django.test import SimpleTestCase

from ...utils import setup


class GetAvailableLanguagesTagTests(SimpleTestCase):
    libraries = {'i18n': 'django.templatetags.i18n'}

    @setup({'i18n12': '{% load i18n %}'
                      '{% get_available_languages as langs %}{% for lang in langs %}'
                      '{% if lang.0 == "de" %}{{ lang.0 }}{% endif %}{% endfor %}'})
    def test_i18n12(self):
        output = self.engine.render_to_string('i18n12')
        self.assertEqual(output, 'de')
