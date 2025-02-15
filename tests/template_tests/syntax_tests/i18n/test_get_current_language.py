from template_tests.utils import setup

from thibaud.template import TemplateSyntaxError
from thibaud.test import SimpleTestCase


class I18nGetCurrentLanguageTagTests(SimpleTestCase):
    libraries = {"i18n": "thibaud.templatetags.i18n"}

    @setup({"template": "{% load i18n %} {% get_current_language %}"})
    def test_no_as_var(self):
        msg = (
            "'get_current_language' requires 'as variable' (got "
            "['get_current_language'])"
        )
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string("template")
