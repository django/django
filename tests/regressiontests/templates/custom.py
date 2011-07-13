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
        self.assertEqual(tag.__name__, name)
        self.assertEqual(tag.__doc__, 'Expected %s __doc__' % name)
        self.assertEqual(tag.__dict__['anything'], 'Expected %s __dict__' % name)

    def test_simple_tags(self):
        c = template.Context({'value': 42})

        t = template.Template('{% load custom %}{% no_params %}')
        self.assertEqual(t.render(c), u'no_params - Expected result')

        t = template.Template('{% load custom %}{% one_param 37 %}')
        self.assertEqual(t.render(c), u'one_param - Expected result: 37')

        t = template.Template('{% load custom %}{% explicit_no_context 37 %}')
        self.assertEqual(t.render(c), u'explicit_no_context - Expected result: 37')

        t = template.Template('{% load custom %}{% no_params_with_context %}')
        self.assertEqual(t.render(c), u'no_params_with_context - Expected result (context value: 42)')

        t = template.Template('{% load custom %}{% params_and_context 37 %}')
        self.assertEqual(t.render(c), u'params_and_context - Expected result (context value: 42): 37')

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

    def test_inclusion_tags(self):
        c = template.Context({'value': 42})

        t = template.Template('{% load custom %}{% inclusion_no_params %}')
        self.assertEqual(t.render(c), u'inclusion_no_params - Expected result\n')

        t = template.Template('{% load custom %}{% inclusion_one_param 37 %}')
        self.assertEqual(t.render(c), u'inclusion_one_param - Expected result: 37\n')

        t = template.Template('{% load custom %}{% inclusion_explicit_no_context 37 %}')
        self.assertEqual(t.render(c), u'inclusion_explicit_no_context - Expected result: 37\n')

        t = template.Template('{% load custom %}{% inclusion_no_params_with_context %}')
        self.assertEqual(t.render(c), u'inclusion_no_params_with_context - Expected result (context value: 42)\n')

        t = template.Template('{% load custom %}{% inclusion_params_and_context 37 %}')
        self.assertEqual(t.render(c), u'inclusion_params_and_context - Expected result (context value: 42): 37\n')

    def test_inclusion_tags_from_template(self):
        c = template.Context({'value': 42})

        t = template.Template('{% load custom %}{% inclusion_no_params_from_template %}')
        self.assertEqual(t.render(c), u'inclusion_no_params_from_template - Expected result\n')

        t = template.Template('{% load custom %}{% inclusion_one_param_from_template 37 %}')
        self.assertEqual(t.render(c), u'inclusion_one_param_from_template - Expected result: 37\n')

        t = template.Template('{% load custom %}{% inclusion_explicit_no_context_from_template 37 %}')
        self.assertEqual(t.render(c), u'inclusion_explicit_no_context_from_template - Expected result: 37\n')

        t = template.Template('{% load custom %}{% inclusion_no_params_with_context_from_template %}')
        self.assertEqual(t.render(c), u'inclusion_no_params_with_context_from_template - Expected result (context value: 42)\n')

        t = template.Template('{% load custom %}{% inclusion_params_and_context_from_template 37 %}')
        self.assertEqual(t.render(c), u'inclusion_params_and_context_from_template - Expected result (context value: 42): 37\n')

    def test_inclusion_tag_registration(self):
        # Test that the decorators preserve the decorated function's docstring, name and attributes.
        self.verify_tag(custom.inclusion_no_params, 'inclusion_no_params')
        self.verify_tag(custom.inclusion_one_param, 'inclusion_one_param')
        self.verify_tag(custom.inclusion_explicit_no_context, 'inclusion_explicit_no_context')
        self.verify_tag(custom.inclusion_no_params_with_context, 'inclusion_no_params_with_context')
        self.verify_tag(custom.inclusion_params_and_context, 'inclusion_params_and_context')

    def test_15070_current_app(self):
        """
        Test that inclusion tag passes down `current_app` of context to the
        Context of the included/rendered template as well.
        """
        c = template.Context({})
        t = template.Template('{% load custom %}{% inclusion_tag_current_app %}')
        self.assertEqual(t.render(c).strip(), u'None')

        c.current_app = 'advanced'
        self.assertEqual(t.render(c).strip(), u'advanced')

    def test_15070_use_l10n(self):
        """
        Test that inclusion tag passes down `use_l10n` of context to the
        Context of the included/rendered template as well.
        """
        c = template.Context({})
        t = template.Template('{% load custom %}{% inclusion_tag_use_l10n %}')
        self.assertEqual(t.render(c).strip(), u'None')

        c.use_l10n = True
        self.assertEqual(t.render(c).strip(), u'True')

    def test_assignment_tags(self):
        c = template.Context({'value': 42})

        t = template.Template('{% load custom %}{% assignment_no_params as var %}The result is: {{ var }}')
        self.assertEqual(t.render(c), u'The result is: assignment_no_params - Expected result')

        t = template.Template('{% load custom %}{% assignment_one_param 37 as var %}The result is: {{ var }}')
        self.assertEqual(t.render(c), u'The result is: assignment_one_param - Expected result: 37')

        t = template.Template('{% load custom %}{% assignment_explicit_no_context 37 as var %}The result is: {{ var }}')
        self.assertEqual(t.render(c), u'The result is: assignment_explicit_no_context - Expected result: 37')

        t = template.Template('{% load custom %}{% assignment_no_params_with_context as var %}The result is: {{ var }}')
        self.assertEqual(t.render(c), u'The result is: assignment_no_params_with_context - Expected result (context value: 42)')

        t = template.Template('{% load custom %}{% assignment_params_and_context 37 as var %}The result is: {{ var }}')
        self.assertEqual(t.render(c), u'The result is: assignment_params_and_context - Expected result (context value: 42): 37')

        self.assertRaisesRegexp(template.TemplateSyntaxError,
            "'assignment_one_param' tag takes at least 2 arguments and the second last argument must be 'as'",
            template.Template, '{% load custom %}{% assignment_one_param 37 %}The result is: {{ var }}')

        self.assertRaisesRegexp(template.TemplateSyntaxError,
            "'assignment_one_param' tag takes at least 2 arguments and the second last argument must be 'as'",
            template.Template, '{% load custom %}{% assignment_one_param 37 as %}The result is: {{ var }}')

        self.assertRaisesRegexp(template.TemplateSyntaxError,
            "'assignment_one_param' tag takes at least 2 arguments and the second last argument must be 'as'",
            template.Template, '{% load custom %}{% assignment_one_param 37 ass var %}The result is: {{ var }}')

    def test_assignment_tag_registration(self):
        # Test that the decorators preserve the decorated function's docstring, name and attributes.
        self.verify_tag(custom.assignment_no_params, 'assignment_no_params')
        self.verify_tag(custom.assignment_one_param, 'assignment_one_param')
        self.verify_tag(custom.assignment_explicit_no_context, 'assignment_explicit_no_context')
        self.verify_tag(custom.assignment_no_params_with_context, 'assignment_no_params_with_context')
        self.verify_tag(custom.assignment_params_and_context, 'assignment_params_and_context')

    def test_assignment_tag_missing_context(self):
        # That the 'context' parameter must be present when takes_context is True
        def an_assignment_tag_without_parameters(arg):
            """Expected __doc__"""
            return "Expected result"

        register = template.Library()
        decorator = register.assignment_tag(takes_context=True)

        self.assertRaisesRegexp(template.TemplateSyntaxError,
            "Any tag function decorated with takes_context=True must have a first argument of 'context'",
            decorator, an_assignment_tag_without_parameters)
