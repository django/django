from template_tests.utils import setup

from django.template import TemplateSyntaxError
from django.test import SimpleTestCase


class I18nLanguageTagTests(SimpleTestCase):
    libraries = {"i18n": "django.templatetags.i18n"}

    @setup({"i18n_language": "{% load i18n %} {% language %} {% endlanguage %}"})
    def test_no_arg(self):
        with self.assertRaisesMessage(
            TemplateSyntaxError, "'language' takes one argument (language)"
        ):
            self.engine.render_to_string("i18n_language")
