import os

from django.template import Context, Engine, TemplateSyntaxError
from django.template.base import Node
from django.template.library import InvalidTemplateLibrary
from django.test import SimpleTestCase
from django.test.utils import extend_sys_path

from .templatetags import custom, inclusion
from .utils import ROOT

LIBRARIES = {
    "custom": "template_tests.templatetags.custom",
    "inclusion": "template_tests.templatetags.inclusion",
}


class CustomFilterTests(SimpleTestCase):
    def test_filter(self):
        engine = Engine(libraries=LIBRARIES)
        t = engine.from_string("{% load custom %}{{ string|trim:5 }}")
        self.assertEqual(
            t.render(Context({"string": "abcdefghijklmnopqrstuvwxyz"})), "abcde"
        )

    def test_decorated_filter(self):
        engine = Engine(libraries=LIBRARIES)
        t = engine.from_string("{% load custom %}{{ name|make_data_div }}")
        self.assertEqual(
            t.render(Context({"name": "foo"})), '<div data-name="foo"></div>'
        )


class TagTestCase(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine(app_dirs=True, libraries=LIBRARIES)
        super().setUpClass()

    def verify_tag(self, tag, name):
        self.assertEqual(tag.__name__, name)
        self.assertEqual(tag.__doc__, "Expected %s __doc__" % name)
        self.assertEqual(tag.__dict__["anything"], "Expected %s __dict__" % name)


class SimpleTagTests(TagTestCase):
    def test_simple_tags(self):
        c = Context({"value": 42})

        templates = [
            ("{% load custom %}{% no_params %}", "no_params - Expected result"),
            ("{% load custom %}{% one_param 37 %}", "one_param - Expected result: 37"),
            (
                "{% load custom %}{% explicit_no_context 37 %}",
                "explicit_no_context - Expected result: 37",
            ),
            (
                "{% load custom %}{% no_params_with_context %}",
                "no_params_with_context - Expected result (context value: 42)",
            ),
            (
                "{% load custom %}{% params_and_context 37 %}",
                "params_and_context - Expected result (context value: 42): 37",
            ),
            (
                "{% load custom %}{% simple_two_params 37 42 %}",
                "simple_two_params - Expected result: 37, 42",
            ),
            (
                "{% load custom %}{% simple_keyword_only_param kwarg=37 %}",
                "simple_keyword_only_param - Expected result: 37",
            ),
            (
                "{% load custom %}{% simple_keyword_only_default %}",
                "simple_keyword_only_default - Expected result: 42",
            ),
            (
                "{% load custom %}{% simple_keyword_only_default kwarg=37 %}",
                "simple_keyword_only_default - Expected result: 37",
            ),
            (
                "{% load custom %}{% simple_one_default 37 %}",
                "simple_one_default - Expected result: 37, hi",
            ),
            (
                '{% load custom %}{% simple_one_default 37 two="hello" %}',
                "simple_one_default - Expected result: 37, hello",
            ),
            (
                '{% load custom %}{% simple_one_default one=99 two="hello" %}',
                "simple_one_default - Expected result: 99, hello",
            ),
            (
                "{% load custom %}{% simple_one_default 37 42 %}",
                "simple_one_default - Expected result: 37, 42",
            ),
            (
                "{% load custom %}{% simple_unlimited_args 37 %}",
                "simple_unlimited_args - Expected result: 37, hi",
            ),
            (
                "{% load custom %}{% simple_unlimited_args 37 42 56 89 %}",
                "simple_unlimited_args - Expected result: 37, 42, 56, 89",
            ),
            (
                "{% load custom %}{% simple_only_unlimited_args %}",
                "simple_only_unlimited_args - Expected result: ",
            ),
            (
                "{% load custom %}{% simple_only_unlimited_args 37 42 56 89 %}",
                "simple_only_unlimited_args - Expected result: 37, 42, 56, 89",
            ),
            (
                "{% load custom %}"
                '{% simple_unlimited_args_kwargs 37 40|add:2 56 eggs="scrambled" '
                "four=1|add:3 %}",
                "simple_unlimited_args_kwargs - Expected result: 37, 42, 56 / "
                "eggs=scrambled, four=4",
            ),
        ]

        for entry in templates:
            t = self.engine.from_string(entry[0])
            self.assertEqual(t.render(c), entry[1])

        for entry in templates:
            t = self.engine.from_string(
                "%s as var %%}Result: {{ var }}" % entry[0][0:-2]
            )
            self.assertEqual(t.render(c), "Result: %s" % entry[1])

    def test_simple_tag_errors(self):
        errors = [
            (
                "'simple_one_default' received unexpected keyword argument 'three'",
                '{% load custom %}{% simple_one_default 99 two="hello" three="foo" %}',
            ),
            (
                "'simple_two_params' received too many positional arguments",
                "{% load custom %}{% simple_two_params 37 42 56 %}",
            ),
            (
                "'simple_one_default' received too many positional arguments",
                "{% load custom %}{% simple_one_default 37 42 56 %}",
            ),
            (
                "'simple_keyword_only_param' did not receive value(s) for the "
                "argument(s): 'kwarg'",
                "{% load custom %}{% simple_keyword_only_param %}",
            ),
            (
                "'simple_keyword_only_param' received multiple values for "
                "keyword argument 'kwarg'",
                "{% load custom %}{% simple_keyword_only_param kwarg=42 kwarg=37 %}",
            ),
            (
                "'simple_keyword_only_default' received multiple values for "
                "keyword argument 'kwarg'",
                "{% load custom %}{% simple_keyword_only_default kwarg=42 "
                "kwarg=37 %}",
            ),
            (
                "'simple_unlimited_args_kwargs' received some positional argument(s) "
                "after some keyword argument(s)",
                "{% load custom %}"
                "{% simple_unlimited_args_kwargs 37 40|add:2 "
                'eggs="scrambled" 56 four=1|add:3 %}',
            ),
            (
                "'simple_unlimited_args_kwargs' received multiple values for keyword "
                "argument 'eggs'",
                "{% load custom %}"
                "{% simple_unlimited_args_kwargs 37 "
                'eggs="scrambled" eggs="scrambled" %}',
            ),
        ]

        for entry in errors:
            with self.assertRaisesMessage(TemplateSyntaxError, entry[0]):
                self.engine.from_string(entry[1])

        for entry in errors:
            with self.assertRaisesMessage(TemplateSyntaxError, entry[0]):
                self.engine.from_string("%s as var %%}" % entry[1][0:-2])

    def test_simple_tag_escaping_autoescape_off(self):
        c = Context({"name": "Jack & Jill"}, autoescape=False)
        t = self.engine.from_string("{% load custom %}{% escape_naive %}")
        self.assertEqual(t.render(c), "Hello Jack & Jill!")

    def test_simple_tag_naive_escaping(self):
        c = Context({"name": "Jack & Jill"})
        t = self.engine.from_string("{% load custom %}{% escape_naive %}")
        self.assertEqual(t.render(c), "Hello Jack &amp; Jill!")

    def test_simple_tag_explicit_escaping(self):
        # Check we don't double escape
        c = Context({"name": "Jack & Jill"})
        t = self.engine.from_string("{% load custom %}{% escape_explicit %}")
        self.assertEqual(t.render(c), "Hello Jack &amp; Jill!")

    def test_simple_tag_format_html_escaping(self):
        # Check we don't double escape
        c = Context({"name": "Jack & Jill"})
        t = self.engine.from_string("{% load custom %}{% escape_format_html %}")
        self.assertEqual(t.render(c), "Hello Jack &amp; Jill!")

    def test_simple_tag_registration(self):
        # The decorators preserve the decorated function's docstring, name,
        # and attributes.
        self.verify_tag(custom.no_params, "no_params")
        self.verify_tag(custom.one_param, "one_param")
        self.verify_tag(custom.explicit_no_context, "explicit_no_context")
        self.verify_tag(custom.no_params_with_context, "no_params_with_context")
        self.verify_tag(custom.params_and_context, "params_and_context")
        self.verify_tag(
            custom.simple_unlimited_args_kwargs, "simple_unlimited_args_kwargs"
        )
        self.verify_tag(
            custom.simple_tag_without_context_parameter,
            "simple_tag_without_context_parameter",
        )

    def test_simple_tag_missing_context(self):
        # The 'context' parameter must be present when takes_context is True
        msg = (
            "'simple_tag_without_context_parameter' is decorated with "
            "takes_context=True so it must have a first argument of 'context'"
        )
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.from_string(
                "{% load custom %}{% simple_tag_without_context_parameter 123 %}"
            )

    def test_simple_tag_missing_context_no_params(self):
        msg = (
            "'simple_tag_takes_context_without_params' is decorated with "
            "takes_context=True so it must have a first argument of 'context'"
        )
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.from_string(
                "{% load custom %}{% simple_tag_takes_context_without_params %}"
            )


class SimpleBlockTagTests(TagTestCase):
    def test_simple_block_tags(self):
        c = Context({"value": 42})

        templates = [
            (
                "{% load custom %}{% div %}content{% enddiv %}",
                "<div id='test'>content</div>",
            ),
            (
                "{% load custom %}{% one_param_block 37 %}inner"
                "{% endone_param_block %}",
                "one_param_block - Expected result: 37 with content inner",
            ),
            (
                "{% load custom %}{% explicit_no_context_block 37 %}inner"
                "{% endexplicit_no_context_block %}",
                "explicit_no_context_block - Expected result: 37 with content inner",
            ),
            (
                "{% load custom %}{% no_params_with_context_block %}inner"
                "{% endno_params_with_context_block %}",
                "no_params_with_context_block - Expected result (context value: 42) "
                "(content value: inner)",
            ),
            (
                "{% load custom %}{% params_and_context_block 37 %}inner"
                "{% endparams_and_context_block %}",
                "params_and_context_block - Expected result (context value: 42) "
                "(content value: inner): 37",
            ),
            (
                "{% load custom %}{% simple_two_params_block 37 42 %}inner"
                "{% endsimple_two_params_block %}",
                "simple_two_params_block - Expected result (content value: inner): "
                "37, 42",
            ),
            (
                "{% load custom %}{% simple_keyword_only_param_block kwarg=37 %}thirty "
                "seven{% endsimple_keyword_only_param_block %}",
                "simple_keyword_only_param_block - Expected result (content value: "
                "thirty seven): 37",
            ),
            (
                "{% load custom %}{% simple_keyword_only_default_block %}forty two"
                "{% endsimple_keyword_only_default_block %}",
                "simple_keyword_only_default_block - Expected result (content value: "
                "forty two): 42",
            ),
            (
                "{% load custom %}{% simple_keyword_only_default_block kwarg=37 %}"
                "thirty seven{% endsimple_keyword_only_default_block %}",
                "simple_keyword_only_default_block - Expected result (content value: "
                "thirty seven): 37",
            ),
            (
                "{% load custom %}{% simple_one_default_block 37 %}inner"
                "{% endsimple_one_default_block %}",
                "simple_one_default_block - Expected result (content value: inner): "
                "37, hi",
            ),
            (
                '{% load custom %}{% simple_one_default_block 37 two="hello" %}inner'
                "{% endsimple_one_default_block %}",
                "simple_one_default_block - Expected result (content value: inner): "
                "37, hello",
            ),
            (
                '{% load custom %}{% simple_one_default_block one=99 two="hello" %}'
                "inner{% endsimple_one_default_block %}",
                "simple_one_default_block - Expected result (content value: inner): "
                "99, hello",
            ),
            (
                "{% load custom %}{% simple_one_default_block 37 42 %}inner"
                "{% endsimple_one_default_block %}",
                "simple_one_default_block - Expected result (content value: inner): "
                "37, 42",
            ),
            (
                "{% load custom %}{% simple_unlimited_args_block 37 %}thirty seven"
                "{% endsimple_unlimited_args_block %}",
                "simple_unlimited_args_block - Expected result (content value: thirty "
                "seven): 37, hi",
            ),
            (
                "{% load custom %}{% simple_unlimited_args_block 37 42 56 89 %}numbers"
                "{% endsimple_unlimited_args_block %}",
                "simple_unlimited_args_block - Expected result "
                "(content value: numbers): 37, 42, 56, 89",
            ),
            (
                "{% load custom %}{% simple_only_unlimited_args_block %}inner"
                "{% endsimple_only_unlimited_args_block %}",
                "simple_only_unlimited_args_block - Expected result (content value: "
                "inner): ",
            ),
            (
                "{% load custom %}{% simple_only_unlimited_args_block 37 42 56 89 %}"
                "numbers{% endsimple_only_unlimited_args_block %}",
                "simple_only_unlimited_args_block - Expected result "
                "(content value: numbers): 37, 42, 56, 89",
            ),
            (
                "{% load custom %}"
                '{% simple_unlimited_args_kwargs_block 37 40|add:2 56 eggs="scrambled" '
                "four=1|add:3 %}inner content"
                "{% endsimple_unlimited_args_kwargs_block %}",
                "simple_unlimited_args_kwargs_block - Expected result (content value: "
                "inner content): 37, 42, 56 / eggs=scrambled, four=4",
            ),
        ]

        for entry in templates:
            with self.subTest(entry[0]):
                t = self.engine.from_string(entry[0])
                self.assertEqual(t.render(c), entry[1])

    def test_simple_block_tag_errors(self):
        errors = [
            (
                "'simple_one_default_block' received unexpected keyword argument "
                "'three'",
                "{% load custom %}"
                '{% simple_one_default_block 99 two="hello" three="foo" %}'
                "{% endsimple_one_default_block %}",
            ),
            (
                "'simple_two_params_block' received too many positional arguments",
                "{% load custom %}{% simple_two_params_block 37 42 56 %}"
                "{% endsimple_two_params_block %}",
            ),
            (
                "'simple_one_default_block' received too many positional arguments",
                "{% load custom %}{% simple_one_default_block 37 42 56 %}"
                "{% endsimple_one_default_block %}",
            ),
            (
                "'simple_keyword_only_param_block' did not receive value(s) for the "
                "argument(s): 'kwarg'",
                "{% load custom %}{% simple_keyword_only_param_block %}"
                "{% endsimple_keyword_only_param_block %}",
            ),
            (
                "'simple_keyword_only_param_block' received multiple values for "
                "keyword argument 'kwarg'",
                "{% load custom %}"
                "{% simple_keyword_only_param_block kwarg=42 kwarg=37 %}"
                "{% endsimple_keyword_only_param_block %}",
            ),
            (
                "'simple_keyword_only_default_block' received multiple values for "
                "keyword argument 'kwarg'",
                "{% load custom %}{% simple_keyword_only_default_block kwarg=42 "
                "kwarg=37 %}{% endsimple_keyword_only_default_block %}",
            ),
            (
                "'simple_unlimited_args_kwargs_block' received some positional "
                "argument(s) after some keyword argument(s)",
                "{% load custom %}"
                '{% simple_unlimited_args_kwargs_block 37 40|add:2 eggs="scrambled" 56 '
                "four=1|add:3 %}{% endsimple_unlimited_args_kwargs_block %}",
            ),
            (
                "'simple_unlimited_args_kwargs_block' received multiple values for "
                "keyword argument 'eggs'",
                "{% load custom %}"
                "{% simple_unlimited_args_kwargs_block 37 "
                'eggs="scrambled" eggs="scrambled" %}'
                "{% endsimple_unlimited_args_kwargs_block %}",
            ),
            (
                "Unclosed tag on line 1: 'div'. Looking for one of: enddiv.",
                "{% load custom %}{% div %}Some content",
            ),
            (
                "Unclosed tag on line 1: 'simple_one_default_block'. Looking for one "
                "of: endsimple_one_default_block.",
                "{% load custom %}{% simple_one_default_block %}Some content",
            ),
            (
                "'simple_tag_without_content_parameter' must have a first argument "
                "of 'content'",
                "{% load custom %}{% simple_tag_without_content_parameter %}",
            ),
            (
                "'simple_tag_with_context_without_content_parameter' is decorated with "
                "takes_context=True so it must have a first argument of 'context' and "
                "a second argument of 'content'",
                "{% load custom %}"
                "{% simple_tag_with_context_without_content_parameter %}",
            ),
        ]

        for entry in errors:
            with self.subTest(entry[1]):
                with self.assertRaisesMessage(TemplateSyntaxError, entry[0]):
                    self.engine.from_string(entry[1])

    def test_simple_block_tag_escaping_autoescape_off(self):
        c = Context({"name": "Jack & Jill"}, autoescape=False)
        t = self.engine.from_string(
            "{% load custom %}{% escape_naive_block %}{{ name }} again"
            "{% endescape_naive_block %}"
        )
        self.assertEqual(t.render(c), "Hello Jack & Jill: Jack & Jill again!")

    def test_simple_block_tag_naive_escaping(self):
        c = Context({"name": "Jack & Jill"})
        t = self.engine.from_string(
            "{% load custom %}{% escape_naive_block %}{{ name }} again"
            "{% endescape_naive_block %}"
        )
        self.assertEqual(
            t.render(c), "Hello Jack &amp; Jill: Jack &amp;amp; Jill again!"
        )

    def test_simple_block_tag_explicit_escaping(self):
        # Check we don't double escape
        c = Context({"name": "Jack & Jill"})
        t = self.engine.from_string(
            "{% load custom %}{% escape_explicit_block %}again"
            "{% endescape_explicit_block %}"
        )
        self.assertEqual(t.render(c), "Hello Jack &amp; Jill: again!")

    def test_simple_block_tag_format_html_escaping(self):
        # Check we don't double escape
        c = Context({"name": "Jack & Jill"})
        t = self.engine.from_string(
            "{% load custom %}{% escape_format_html_block %}again"
            "{% endescape_format_html_block %}"
        )
        self.assertEqual(t.render(c), "Hello Jack &amp; Jill: again!")

    def test_simple_block_tag_missing_context(self):
        # The 'context' parameter must be present when takes_context is True
        msg = (
            "'simple_block_tag_without_context_parameter' is decorated with "
            "takes_context=True so it must have a first argument of 'context'"
        )
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.from_string(
                "{% load custom %}{% simple_block_tag_without_context_parameter 123 %}"
                "{% endsimple_block_tag_without_context_parameter %}"
            )

    def test_simple_block_tag_missing_context_no_params(self):
        msg = (
            "'simple_tag_takes_context_without_params_block' is decorated with "
            "takes_context=True so it must have a first argument of 'context'"
        )
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.from_string(
                "{% load custom %}{% simple_tag_takes_context_without_params_block %}"
                "{% endsimple_tag_takes_context_without_params_block %}"
            )

    def test_simple_block_tag_missing_content(self):
        # The 'content' parameter must be present when takes_context is True
        msg = (
            "'simple_block_tag_without_content' must have a first argument of 'content'"
        )
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.from_string(
                "{% load custom %}{% simple_block_tag_without_content %}"
                "{% endsimple_block_tag_without_content %}"
            )

    def test_simple_block_tag_with_context_missing_content(self):
        # The 'content' parameter must be present when takes_context is True
        msg = "'simple_block_tag_with_context_without_content' is decorated with "
        "takes_context=True so it must have a first argument of 'context' and a "
        "second argument of 'content'"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.from_string(
                "{% load custom %}{% simple_block_tag_with_context_without_content %}"
                "{% endsimple_block_tag_with_context_without_content %}"
            )

    def test_simple_block_gets_context(self):
        c = Context({"name": "Jack & Jill"})
        t = self.engine.from_string("{% load custom %}{% div %}{{ name }}{% enddiv %}")
        self.assertEqual(t.render(c), "<div id='test'>Jack &amp; Jill</div>")

    def test_simple_block_capture_as(self):
        c = Context({"name": "Jack & Jill"})
        t = self.engine.from_string(
            "{% load custom %}{% div as div_content %}{{ name }}{% enddiv %}"
            "My div is: {{ div_content }}"
        )
        self.assertEqual(t.render(c), "My div is: <div id='test'>Jack &amp; Jill</div>")

    def test_simple_block_nested(self):
        c = Context({"name": "Jack & Jill"})
        t = self.engine.from_string(
            "{% load custom %}Start{% div id='outer' %}Before{% div id='inner' %}"
            "{{ name }}{% enddiv %}After{% enddiv %}End"
        )
        self.assertEqual(
            t.render(c),
            "Start<div id='outer'>Before<div id='inner'>Jack &amp; Jill</div>After"
            "</div>End",
        )

    def test_different_simple_block_nested(self):
        c = Context({"name": "Jack & Jill"})
        t = self.engine.from_string(
            "{% load custom %}Start{% div id='outer' %}Before"
            "{% simple_keyword_only_default_block %}Inner"
            "{% endsimple_keyword_only_default_block %}"
            "After{% enddiv %}End"
        )
        self.assertEqual(
            t.render(c),
            "Start<div id='outer'>Before"
            "simple_keyword_only_default_block - Expected result (content value: "
            "Inner): 42After</div>End",
        )

    def test_custom_end_tag(self):
        c = Context({"name": "Jack & Jill"})
        t = self.engine.from_string(
            "{% load custom %}{% div_custom_end %}{{ name }}{% divend %}"
        )
        self.assertEqual(t.render(c), "<div>Jack &amp; Jill</div>")

        with self.assertRaisesMessage(
            TemplateSyntaxError,
            "'enddiv_custom_end', expected 'divend'. Did you forget to register or "
            "load this tag?",
        ):
            self.engine.from_string(
                "{% load custom %}{% div_custom_end %}{{ name }}{% enddiv_custom_end %}"
            )


class InclusionTagTests(TagTestCase):
    def test_inclusion_tags(self):
        c = Context({"value": 42})

        templates = [
            (
                "{% load inclusion %}{% inclusion_no_params %}",
                "inclusion_no_params - Expected result\n",
            ),
            (
                "{% load inclusion %}{% inclusion_one_param 37 %}",
                "inclusion_one_param - Expected result: 37\n",
            ),
            (
                "{% load inclusion %}{% inclusion_explicit_no_context 37 %}",
                "inclusion_explicit_no_context - Expected result: 37\n",
            ),
            (
                "{% load inclusion %}{% inclusion_no_params_with_context %}",
                "inclusion_no_params_with_context - Expected result (context value: "
                "42)\n",
            ),
            (
                "{% load inclusion %}{% inclusion_params_and_context 37 %}",
                "inclusion_params_and_context - Expected result (context value: 42): "
                "37\n",
            ),
            (
                "{% load inclusion %}{% inclusion_two_params 37 42 %}",
                "inclusion_two_params - Expected result: 37, 42\n",
            ),
            (
                "{% load inclusion %}{% inclusion_one_default 37 %}",
                "inclusion_one_default - Expected result: 37, hi\n",
            ),
            (
                '{% load inclusion %}{% inclusion_one_default 37 two="hello" %}',
                "inclusion_one_default - Expected result: 37, hello\n",
            ),
            (
                '{% load inclusion %}{% inclusion_one_default one=99 two="hello" %}',
                "inclusion_one_default - Expected result: 99, hello\n",
            ),
            (
                "{% load inclusion %}{% inclusion_one_default 37 42 %}",
                "inclusion_one_default - Expected result: 37, 42\n",
            ),
            (
                "{% load inclusion %}{% inclusion_keyword_only_default kwarg=37 %}",
                "inclusion_keyword_only_default - Expected result: 37\n",
            ),
            (
                "{% load inclusion %}{% inclusion_unlimited_args 37 %}",
                "inclusion_unlimited_args - Expected result: 37, hi\n",
            ),
            (
                "{% load inclusion %}{% inclusion_unlimited_args 37 42 56 89 %}",
                "inclusion_unlimited_args - Expected result: 37, 42, 56, 89\n",
            ),
            (
                "{% load inclusion %}{% inclusion_only_unlimited_args %}",
                "inclusion_only_unlimited_args - Expected result: \n",
            ),
            (
                "{% load inclusion %}{% inclusion_only_unlimited_args 37 42 56 89 %}",
                "inclusion_only_unlimited_args - Expected result: 37, 42, 56, 89\n",
            ),
            (
                "{% load inclusion %}"
                '{% inclusion_unlimited_args_kwargs 37 40|add:2 56 eggs="scrambled" '
                "four=1|add:3 %}",
                "inclusion_unlimited_args_kwargs - Expected result: 37, 42, 56 / "
                "eggs=scrambled, four=4\n",
            ),
        ]

        for entry in templates:
            t = self.engine.from_string(entry[0])
            self.assertEqual(t.render(c), entry[1])

    def test_inclusion_tag_errors(self):
        errors = [
            (
                "'inclusion_one_default' received unexpected keyword argument 'three'",
                "{% load inclusion %}"
                '{% inclusion_one_default 99 two="hello" three="foo" %}',
            ),
            (
                "'inclusion_two_params' received too many positional arguments",
                "{% load inclusion %}{% inclusion_two_params 37 42 56 %}",
            ),
            (
                "'inclusion_one_default' received too many positional arguments",
                "{% load inclusion %}{% inclusion_one_default 37 42 56 %}",
            ),
            (
                "'inclusion_one_default' did not receive value(s) for the argument(s): "
                "'one'",
                "{% load inclusion %}{% inclusion_one_default %}",
            ),
            (
                "'inclusion_keyword_only_default' received multiple values "
                "for keyword argument 'kwarg'",
                "{% load inclusion %}{% inclusion_keyword_only_default "
                "kwarg=37 kwarg=42 %}",
            ),
            (
                "'inclusion_unlimited_args' did not receive value(s) for the "
                "argument(s): 'one'",
                "{% load inclusion %}{% inclusion_unlimited_args %}",
            ),
            (
                "'inclusion_unlimited_args_kwargs' received some positional "
                "argument(s) after some keyword argument(s)",
                "{% load inclusion %}"
                "{% inclusion_unlimited_args_kwargs 37 40|add:2 "
                'eggs="boiled" 56 four=1|add:3 %}',
            ),
            (
                "'inclusion_unlimited_args_kwargs' received multiple values for "
                "keyword argument 'eggs'",
                "{% load inclusion %}"
                "{% inclusion_unlimited_args_kwargs 37 "
                'eggs="scrambled" eggs="scrambled" %}',
            ),
        ]

        for entry in errors:
            with self.assertRaisesMessage(TemplateSyntaxError, entry[0]):
                self.engine.from_string(entry[1])

    def test_include_tag_missing_context(self):
        # The 'context' parameter must be present when takes_context is True
        msg = (
            "'inclusion_tag_without_context_parameter' is decorated with "
            "takes_context=True so it must have a first argument of 'context'"
        )
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.from_string(
                "{% load inclusion %}{% inclusion_tag_without_context_parameter 123 %}"
            )

    def test_include_tag_missing_context_no_params(self):
        msg = (
            "'inclusion_tag_takes_context_without_params' is decorated with "
            "takes_context=True so it must have a first argument of 'context'"
        )
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.from_string(
                "{% load inclusion %}{% inclusion_tag_takes_context_without_params %}"
            )

    def test_inclusion_tags_from_template(self):
        c = Context({"value": 42})

        templates = [
            (
                "{% load inclusion %}{% inclusion_no_params_from_template %}",
                "inclusion_no_params_from_template - Expected result\n",
            ),
            (
                "{% load inclusion %}{% inclusion_one_param_from_template 37 %}",
                "inclusion_one_param_from_template - Expected result: 37\n",
            ),
            (
                "{% load inclusion %}"
                "{% inclusion_explicit_no_context_from_template 37 %}",
                "inclusion_explicit_no_context_from_template - Expected result: 37\n",
            ),
            (
                "{% load inclusion %}"
                "{% inclusion_no_params_with_context_from_template %}",
                "inclusion_no_params_with_context_from_template - Expected result "
                "(context value: 42)\n",
            ),
            (
                "{% load inclusion %}"
                "{% inclusion_params_and_context_from_template 37 %}",
                "inclusion_params_and_context_from_template - Expected result (context "
                "value: 42): 37\n",
            ),
            (
                "{% load inclusion %}{% inclusion_two_params_from_template 37 42 %}",
                "inclusion_two_params_from_template - Expected result: 37, 42\n",
            ),
            (
                "{% load inclusion %}{% inclusion_one_default_from_template 37 %}",
                "inclusion_one_default_from_template - Expected result: 37, hi\n",
            ),
            (
                "{% load inclusion %}{% inclusion_one_default_from_template 37 42 %}",
                "inclusion_one_default_from_template - Expected result: 37, 42\n",
            ),
            (
                "{% load inclusion %}{% inclusion_unlimited_args_from_template 37 %}",
                "inclusion_unlimited_args_from_template - Expected result: 37, hi\n",
            ),
            (
                "{% load inclusion %}"
                "{% inclusion_unlimited_args_from_template 37 42 56 89 %}",
                "inclusion_unlimited_args_from_template - Expected result: 37, 42, 56, "
                "89\n",
            ),
            (
                "{% load inclusion %}{% inclusion_only_unlimited_args_from_template %}",
                "inclusion_only_unlimited_args_from_template - Expected result: \n",
            ),
            (
                "{% load inclusion %}"
                "{% inclusion_only_unlimited_args_from_template 37 42 56 89 %}",
                "inclusion_only_unlimited_args_from_template - Expected result: 37, "
                "42, 56, 89\n",
            ),
        ]

        for entry in templates:
            t = self.engine.from_string(entry[0])
            self.assertEqual(t.render(c), entry[1])

    def test_inclusion_tag_registration(self):
        # The decorators preserve the decorated function's docstring, name,
        # and attributes.
        self.verify_tag(inclusion.inclusion_no_params, "inclusion_no_params")
        self.verify_tag(inclusion.inclusion_one_param, "inclusion_one_param")
        self.verify_tag(
            inclusion.inclusion_explicit_no_context, "inclusion_explicit_no_context"
        )
        self.verify_tag(
            inclusion.inclusion_no_params_with_context,
            "inclusion_no_params_with_context",
        )
        self.verify_tag(
            inclusion.inclusion_params_and_context, "inclusion_params_and_context"
        )
        self.verify_tag(inclusion.inclusion_two_params, "inclusion_two_params")
        self.verify_tag(inclusion.inclusion_one_default, "inclusion_one_default")
        self.verify_tag(inclusion.inclusion_unlimited_args, "inclusion_unlimited_args")
        self.verify_tag(
            inclusion.inclusion_only_unlimited_args, "inclusion_only_unlimited_args"
        )
        self.verify_tag(
            inclusion.inclusion_tag_without_context_parameter,
            "inclusion_tag_without_context_parameter",
        )
        self.verify_tag(inclusion.inclusion_tag_use_l10n, "inclusion_tag_use_l10n")
        self.verify_tag(
            inclusion.inclusion_unlimited_args_kwargs, "inclusion_unlimited_args_kwargs"
        )

    def test_15070_use_l10n(self):
        """
        Inclusion tag passes down `use_l10n` of context to the
        Context of the included/rendered template as well.
        """
        c = Context({})
        t = self.engine.from_string("{% load inclusion %}{% inclusion_tag_use_l10n %}")
        self.assertEqual(t.render(c).strip(), "None")

        c.use_l10n = True
        self.assertEqual(t.render(c).strip(), "True")

    def test_no_render_side_effect(self):
        """
        #23441 -- InclusionNode shouldn't modify its nodelist at render time.
        """
        engine = Engine(app_dirs=True, libraries=LIBRARIES)
        template = engine.from_string("{% load inclusion %}{% inclusion_no_params %}")
        count = template.nodelist.get_nodes_by_type(Node)
        template.render(Context({}))
        self.assertEqual(template.nodelist.get_nodes_by_type(Node), count)

    def test_render_context_is_cleared(self):
        """
        #24555 -- InclusionNode should push and pop the render_context stack
        when rendering. Otherwise, leftover values such as blocks from
        extending can interfere with subsequent rendering.
        """
        engine = Engine(app_dirs=True, libraries=LIBRARIES)
        template = engine.from_string(
            "{% load inclusion %}{% inclusion_extends1 %}{% inclusion_extends2 %}"
        )
        self.assertEqual(template.render(Context({})).strip(), "one\ntwo")


class TemplateTagLoadingTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        cls.egg_dir = os.path.join(ROOT, "eggs")
        super().setUpClass()

    def test_load_error(self):
        msg = (
            "Invalid template library specified. ImportError raised when "
            "trying to load 'template_tests.broken_tag': cannot import name "
            "'Xtemplate'"
        )
        with self.assertRaisesMessage(InvalidTemplateLibrary, msg):
            Engine(libraries={"broken_tag": "template_tests.broken_tag"})

    def test_load_error_egg(self):
        egg_name = "%s/tagsegg.egg" % self.egg_dir
        msg = (
            "Invalid template library specified. ImportError raised when "
            "trying to load 'tagsegg.templatetags.broken_egg': cannot "
            "import name 'Xtemplate'"
        )
        with extend_sys_path(egg_name):
            with self.assertRaisesMessage(InvalidTemplateLibrary, msg):
                Engine(libraries={"broken_egg": "tagsegg.templatetags.broken_egg"})

    def test_load_working_egg(self):
        ttext = "{% load working_egg %}"
        egg_name = "%s/tagsegg.egg" % self.egg_dir
        with extend_sys_path(egg_name):
            engine = Engine(
                libraries={
                    "working_egg": "tagsegg.templatetags.working_egg",
                }
            )
            engine.from_string(ttext)

    def test_load_annotated_function(self):
        Engine(
            libraries={
                "annotated_tag_function": "template_tests.annotated_tag_function",
            }
        )
