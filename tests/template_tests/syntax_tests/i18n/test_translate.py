import inspect
from functools import partial, wraps

from asgiref.local import Local

from django.template import Context, Template, TemplateSyntaxError
from django.templatetags.l10n import LocalizeNode
from django.test import SimpleTestCase, override_settings
from django.utils import translation
from django.utils.safestring import mark_safe
from django.utils.translation import trans_real

from ...utils import setup as base_setup
from .base import MultipleLocaleActivationTestCase, extended_locale_paths


def setup(templates, *args, **kwargs):
    translate_setup = base_setup(templates, *args, **kwargs)
    trans_setup = base_setup(
        {
            name: template.replace("{% translate ", "{% trans ")
            for name, template in templates.items()
        }
    )

    tags = {
        "trans": trans_setup,
        "translate": translate_setup,
    }

    def decorator(func):
        @wraps(func)
        def inner(self, *args):
            signature = inspect.signature(func)
            for tag_name, setup_func in tags.items():
                if "tag_name" in signature.parameters:
                    setup_func(partial(func, tag_name=tag_name))(self)
                else:
                    setup_func(func)(self)

        return inner

    return decorator


class I18nTransTagTests(SimpleTestCase):
    libraries = {"i18n": "django.templatetags.i18n"}

    @setup({"i18n01": "{% load i18n %}{% translate 'xxxyyyxxx' %}"})
    def test_i18n01(self):
        """simple translation of a string delimited by '."""
        output = self.engine.render_to_string("i18n01")
        self.assertEqual(output, "xxxyyyxxx")

    @setup({"i18n02": '{% load i18n %}{% translate "xxxyyyxxx" %}'})
    def test_i18n02(self):
        """simple translation of a string delimited by "."""
        output = self.engine.render_to_string("i18n02")
        self.assertEqual(output, "xxxyyyxxx")

    @setup({"i18n06": '{% load i18n %}{% translate "Page not found" %}'})
    def test_i18n06(self):
        """simple translation of a string to German"""
        with translation.override("de"):
            output = self.engine.render_to_string("i18n06")
        self.assertEqual(output, "Seite nicht gefunden")

    @setup({"i18n09": '{% load i18n %}{% translate "Page not found" noop %}'})
    def test_i18n09(self):
        """simple non-translation (only marking) of a string to German"""
        with translation.override("de"):
            output = self.engine.render_to_string("i18n09")
        self.assertEqual(output, "Page not found")

    @setup({"i18n20": "{% load i18n %}{% translate andrew %}"})
    def test_i18n20(self):
        output = self.engine.render_to_string("i18n20", {"andrew": "a & b"})
        self.assertEqual(output, "a &amp; b")

    @setup({"i18n22": "{% load i18n %}{% translate andrew %}"})
    def test_i18n22(self):
        output = self.engine.render_to_string("i18n22", {"andrew": mark_safe("a & b")})
        self.assertEqual(output, "a & b")

    @setup(
        {
            "i18n23": (
                '{% load i18n %}{% translate "Page not found"|capfirst|slice:"6:" %}'
            )
        }
    )
    def test_i18n23(self):
        """Using filters with the {% translate %} tag (#5972)."""
        with translation.override("de"):
            output = self.engine.render_to_string("i18n23")
        self.assertEqual(output, "nicht gefunden")

    @setup({"i18n24": "{% load i18n %}{% translate 'Page not found'|upper %}"})
    def test_i18n24(self):
        with translation.override("de"):
            output = self.engine.render_to_string("i18n24")
        self.assertEqual(output, "SEITE NICHT GEFUNDEN")

    @setup({"i18n25": "{% load i18n %}{% translate somevar|upper %}"})
    def test_i18n25(self):
        with translation.override("de"):
            output = self.engine.render_to_string(
                "i18n25", {"somevar": "Page not found"}
            )
        self.assertEqual(output, "SEITE NICHT GEFUNDEN")

    # trans tag with as var
    @setup(
        {
            "i18n35": (
                '{% load i18n %}{% translate "Page not found" as page_not_found %}'
                "{{ page_not_found }}"
            )
        }
    )
    def test_i18n35(self):
        with translation.override("de"):
            output = self.engine.render_to_string("i18n35")
        self.assertEqual(output, "Seite nicht gefunden")

    @setup(
        {
            "i18n36": (
                '{% load i18n %}{% translate "Page not found" noop as page_not_found %}'
                "{{ page_not_found }}"
            )
        }
    )
    def test_i18n36(self):
        with translation.override("de"):
            output = self.engine.render_to_string("i18n36")
        self.assertEqual(output, "Page not found")

    @setup({"template": "{% load i18n %}{% translate %}A}"})
    def test_syntax_error_no_arguments(self, tag_name):
        msg = "'{}' takes at least one argument".format(tag_name)
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string("template")

    @setup({"template": '{% load i18n %}{% translate "Yes" badoption %}'})
    def test_syntax_error_bad_option(self, tag_name):
        msg = "Unknown argument for '{}' tag: 'badoption'".format(tag_name)
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string("template")

    @setup({"template": '{% load i18n %}{% translate "Yes" as %}'})
    def test_syntax_error_missing_assignment(self, tag_name):
        msg = "No argument provided to the '{}' tag for the as option.".format(tag_name)
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string("template")

    @setup({"template": '{% load i18n %}{% translate "Yes" as var context %}'})
    def test_syntax_error_missing_context(self, tag_name):
        msg = "No argument provided to the '{}' tag for the context option.".format(
            tag_name
        )
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string("template")

    @setup({"template": '{% load i18n %}{% translate "Yes" context as var %}'})
    def test_syntax_error_context_as(self, tag_name):
        msg = (
            f"Invalid argument 'as' provided to the '{tag_name}' tag for the context "
            f"option"
        )
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string("template")

    @setup({"template": '{% load i18n %}{% translate "Yes" context noop %}'})
    def test_syntax_error_context_noop(self, tag_name):
        msg = (
            f"Invalid argument 'noop' provided to the '{tag_name}' tag for the context "
            f"option"
        )
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string("template")

    @setup({"template": '{% load i18n %}{% translate "Yes" noop noop %}'})
    def test_syntax_error_duplicate_option(self):
        msg = "The 'noop' option was specified more than once."
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string("template")

    @setup({"template": '{% load i18n %}{% translate "%s" %}'})
    def test_trans_tag_using_a_string_that_looks_like_str_fmt(self):
        output = self.engine.render_to_string("template")
        self.assertEqual(output, "%s")


class TranslationTransTagTests(SimpleTestCase):
    tag_name = "trans"

    def get_template(self, template_string):
        return Template(
            template_string.replace("{{% translate ", "{{% {}".format(self.tag_name))
        )

    @override_settings(LOCALE_PATHS=extended_locale_paths)
    def test_template_tags_pgettext(self):
        """{% translate %} takes message contexts into account (#14806)."""
        trans_real._active = Local()
        trans_real._translations = {}
        with translation.override("de"):
            # Nonexistent context...
            t = self.get_template(
                '{% load i18n %}{% translate "May" context "nonexistent" %}'
            )
            rendered = t.render(Context())
            self.assertEqual(rendered, "May")

            # Existing context... using a literal
            t = self.get_template(
                '{% load i18n %}{% translate "May" context "month name" %}'
            )
            rendered = t.render(Context())
            self.assertEqual(rendered, "Mai")
            t = self.get_template('{% load i18n %}{% translate "May" context "verb" %}')
            rendered = t.render(Context())
            self.assertEqual(rendered, "Kann")

            # Using a variable
            t = self.get_template(
                '{% load i18n %}{% translate "May" context message_context %}'
            )
            rendered = t.render(Context({"message_context": "month name"}))
            self.assertEqual(rendered, "Mai")
            t = self.get_template(
                '{% load i18n %}{% translate "May" context message_context %}'
            )
            rendered = t.render(Context({"message_context": "verb"}))
            self.assertEqual(rendered, "Kann")

            # Using a filter
            t = self.get_template(
                '{% load i18n %}{% translate "May" context message_context|lower %}'
            )
            rendered = t.render(Context({"message_context": "MONTH NAME"}))
            self.assertEqual(rendered, "Mai")
            t = self.get_template(
                '{% load i18n %}{% translate "May" context message_context|lower %}'
            )
            rendered = t.render(Context({"message_context": "VERB"}))
            self.assertEqual(rendered, "Kann")

            # Using 'as'
            t = self.get_template(
                '{% load i18n %}{% translate "May" context "month name" as var %}'
                "Value: {{ var }}"
            )
            rendered = t.render(Context())
            self.assertEqual(rendered, "Value: Mai")
            t = self.get_template(
                '{% load i18n %}{% translate "May" as var context "verb" %}Value: '
                "{{ var }}"
            )
            rendered = t.render(Context())
            self.assertEqual(rendered, "Value: Kann")


class TranslationTranslateTagTests(TranslationTransTagTests):
    tag_name = "translate"


class MultipleLocaleActivationTransTagTests(MultipleLocaleActivationTestCase):
    tag_name = "trans"

    def get_template(self, template_string):
        return Template(
            template_string.replace("{{% translate ", "{{% {}".format(self.tag_name))
        )

    def test_single_locale_activation(self):
        """
        Simple baseline behavior with one locale for all the supported i18n
        constructs.
        """
        with translation.override("fr"):
            self.assertEqual(
                self.get_template("{% load i18n %}{% translate 'Yes' %}").render(
                    Context({})
                ),
                "Oui",
            )

    def test_multiple_locale_trans(self):
        with translation.override("de"):
            t = self.get_template("{% load i18n %}{% translate 'No' %}")
        with translation.override(self._old_language), translation.override("nl"):
            self.assertEqual(t.render(Context({})), "Nee")

    def test_multiple_locale_deactivate_trans(self):
        with translation.override("de", deactivate=True):
            t = self.get_template("{% load i18n %}{% translate 'No' %}")
        with translation.override("nl"):
            self.assertEqual(t.render(Context({})), "Nee")

    def test_multiple_locale_direct_switch_trans(self):
        with translation.override("de"):
            t = self.get_template("{% load i18n %}{% translate 'No' %}")
        with translation.override("nl"):
            self.assertEqual(t.render(Context({})), "Nee")


class MultipleLocaleActivationTranslateTagTests(MultipleLocaleActivationTransTagTests):
    tag_name = "translate"


class LocalizeNodeTests(SimpleTestCase):
    def test_repr(self):
        node = LocalizeNode(nodelist=[], use_l10n=True)
        self.assertEqual(repr(node), "<LocalizeNode>")
