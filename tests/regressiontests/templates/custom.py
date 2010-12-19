from django import template
from django.utils.unittest import TestCase
from templatetags import custom

class CustomFilterTests(TestCase):
    def test_filter(self):
        t = template.Template("{% load custom %}{{ string|trim:5 }}")
        self.assertEqual(
            t.render(template.Context({"string": "abcdefghijklmnopqrstuvwxyz"})),
            u"abcde"
        )


class CustomTagTests(TestCase):
    def verify_tag(self, tag, name):
        self.assertEquals(tag.__name__, name)
        self.assertEquals(tag.__doc__, 'Expected %s __doc__' % name)
        self.assertEquals(tag.__dict__['anything'], 'Expected %s __dict__' % name)

    def test_simple_tags(self):
        c = template.Context({'value': 42})

        t = template.Template('{% load custom %}{% no_params %}')
        self.assertEquals(t.render(c), u'no_params - Expected result')

        t = template.Template('{% load custom %}{% one_param 37 %}')
        self.assertEquals(t.render(c), u'one_param - Expected result: 37')

        t = template.Template('{% load custom %}{% explicit_no_context 37 %}')
        self.assertEquals(t.render(c), u'explicit_no_context - Expected result: 37')

        t = template.Template('{% load custom %}{% no_params_with_context %}')
        self.assertEquals(t.render(c), u'no_params_with_context - Expected result (context value: 42)')

        t = template.Template('{% load custom %}{% params_and_context 37 %}')
        self.assertEquals(t.render(c), u'params_and_context - Expected result (context value: 42): 37')

    def test_simple_tag_registration(self):
        # Test that the decorators preserve the decorated function's docstring, name and attributes.
        self.verify_tag(custom.no_params, 'no_params')
        self.verify_tag(custom.one_param, 'one_param')
        self.verify_tag(custom.explicit_no_context, 'explicit_no_context')
        self.verify_tag(custom.no_params_with_context, 'no_params_with_context')
        self.verify_tag(custom.params_and_context, 'params_and_context')

    def test_simple_tag_missing_context(self):
        # That the 'context' parameter must be present when takes_context is True
        def a_simple_tag_without_parameters(arg):
            """Expected __doc__"""
            return "Expected result"

        register = template.Library()
        decorator = register.simple_tag(takes_context=True)
        self.assertRaises(template.TemplateSyntaxError, decorator, a_simple_tag_without_parameters)
