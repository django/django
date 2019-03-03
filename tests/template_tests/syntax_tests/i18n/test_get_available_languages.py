from django.template import TemplateSyntaxError
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

    @setup({'syntax_i18n': '{% load i18n %}{% get_available_languages a langs %}'})
    def test_no_as_var(self):
        msg = "'get_available_languages' requires 'as variable' (got ['get_available_languages', 'a', 'langs'])"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('syntax_i18n')
