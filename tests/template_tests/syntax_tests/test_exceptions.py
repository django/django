from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.test import SimpleTestCase

from ..utils import setup
from .test_extends import inheritance_templates


class ExceptionsTests(SimpleTestCase):

    @setup({'exception01': "{% extends 'nonexistent' %}"})
    def test_exception01(self):
        """
        Raise exception for invalid template name
        """
        with self.assertRaises(TemplateDoesNotExist):
            self.engine.render_to_string('exception01')

    @setup({'exception02': '{% extends nonexistent %}'})
    def test_exception02(self):
        """
        Raise exception for invalid variable template name
        """
        if self.engine.string_if_invalid:
            with self.assertRaises(TemplateDoesNotExist):
                self.engine.render_to_string('exception02')
        else:
            with self.assertRaises(TemplateSyntaxError):
                self.engine.render_to_string('exception02')

    @setup(
        {'exception03': "{% extends 'inheritance01' %}"
                        "{% block first %}2{% endblock %}{% extends 'inheritance16' %}"},
        inheritance_templates,
    )
    def test_exception03(self):
        """
        Raise exception for extra {% extends %} tags
        """
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('exception03')

    @setup(
        {'exception04': "{% extends 'inheritance17' %}{% block first %}{% echo 400 %}5678{% endblock %}"},
        inheritance_templates,
    )
    def test_exception04(self):
        """
        Raise exception for custom tags used in child with {% load %} tag in parent, not in child
        """
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('exception04')

    @setup({'exception05': '{% block first %}{{ block.super }}{% endblock %}'})
    def test_exception05(self):
        """
        Raise exception for block.super used in base template
        """
        with self.assertRaises(TemplateSyntaxError):
            self.engine.render_to_string('exception05')
