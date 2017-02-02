from threading import local

from django.template import Context, Template, TemplateSyntaxError
from django.test import SimpleTestCase, override_settings
from django.utils import translation
from django.utils.safestring import mark_safe
from django.utils.translation import trans_real

from ...utils import setup
from .base import MultipleLocaleActivationTestCase, extended_locale_paths


class I18nTransTagTests(SimpleTestCase):
    libraries = {'i18n': 'django.templatetags.i18n'}

    @setup({'i18n01': '{% load i18n %}{% trans \'xxxyyyxxx\' %}'})
    def test_i18n01(self):
        """simple translation of a string delimited by '."""
        output = self.engine.render_to_string('i18n01')
        self.assertEqual(output, 'xxxyyyxxx')

    @setup({'i18n02': '{% load i18n %}{% trans "xxxyyyxxx" %}'})
    def test_i18n02(self):
        """simple translation of a string delimited by "."""
        output = self.engine.render_to_string('i18n02')
        self.assertEqual(output, 'xxxyyyxxx')

    @setup({'i18n06': '{% load i18n %}{% trans "Page not found" %}'})
    def test_i18n06(self):
        """simple translation of a string to German"""
        with translation.override('de'):
            output = self.engine.render_to_string('i18n06')
        self.assertEqual(output, 'Seite nicht gefunden')

    @setup({'i18n09': '{% load i18n %}{% trans "Page not found" noop %}'})
    def test_i18n09(self):
        """simple non-translation (only marking) of a string to German"""
        with translation.override('de'):
            output = self.engine.render_to_string('i18n09')
        self.assertEqual(output, 'Page not found')

    @setup({'i18n20': '{% load i18n %}{% trans andrew %}'})
    def test_i18n20(self):
        output = self.engine.render_to_string('i18n20', {'andrew': 'a & b'})
        self.assertEqual(output, 'a &amp; b')

    @setup({'i18n22': '{% load i18n %}{% trans andrew %}'})
    def test_i18n22(self):
        output = self.engine.render_to_string('i18n22', {'andrew': mark_safe('a & b')})
        self.assertEqual(output, 'a & b')

    @setup({'i18n23': '{% load i18n %}{% trans "Page not found"|capfirst|slice:"6:" %}'})
    def test_i18n23(self):
        """Using filters with the {% trans %} tag (#5972)."""
        with translation.override('de'):
            output = self.engine.render_to_string('i18n23')
        self.assertEqual(output, 'nicht gefunden')

    @setup({'i18n24': '{% load i18n %}{% trans \'Page not found\'|upper %}'})
    def test_i18n24(self):
        with translation.override('de'):
            output = self.engine.render_to_string('i18n24')
        self.assertEqual(output, 'SEITE NICHT GEFUNDEN')

    @setup({'i18n25': '{% load i18n %}{% trans somevar|upper %}'})
    def test_i18n25(self):
        with translation.override('de'):
            output = self.engine.render_to_string('i18n25', {'somevar': 'Page not found'})
        self.assertEqual(output, 'SEITE NICHT GEFUNDEN')

    # trans tag with as var
    @setup({'i18n35': '{% load i18n %}{% trans "Page not found" as page_not_found %}{{ page_not_found }}'})
    def test_i18n35(self):
        with translation.override('de'):
            output = self.engine.render_to_string('i18n35')
        self.assertEqual(output, 'Seite nicht gefunden')

    @setup({'i18n36': '{% load i18n %}'
                      '{% trans "Page not found" noop as page_not_found %}{{ page_not_found }}'})
    def test_i18n36(self):
        with translation.override('de'):
            output = self.engine.render_to_string('i18n36')
        self.assertEqual(output, 'Page not found')

    @setup({'template': '{% load i18n %}{% trans %}A}'})
    def test_syntax_error_no_arguments(self):
        msg = "'trans' takes at least one argument"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('template')

    @setup({'template': '{% load i18n %}{% trans "Yes" badoption %}'})
    def test_syntax_error_bad_option(self):
        msg = "Unknown argument for 'trans' tag: 'badoption'"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('template')

    @setup({'template': '{% load i18n %}{% trans "Yes" as %}'})
    def test_syntax_error_missing_assignment(self):
        msg = "No argument provided to the 'trans' tag for the as option."
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('template')

    @setup({'template': '{% load i18n %}{% trans "Yes" as var context %}'})
    def test_syntax_error_missing_context(self):
        msg = "No argument provided to the 'trans' tag for the context option."
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('template')

    @setup({'template': '{% load i18n %}{% trans "Yes" context as var %}'})
    def test_syntax_error_context_as(self):
        msg = "Invalid argument 'as' provided to the 'trans' tag for the context option"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('template')

    @setup({'template': '{% load i18n %}{% trans "Yes" context noop %}'})
    def test_syntax_error_context_noop(self):
        msg = "Invalid argument 'noop' provided to the 'trans' tag for the context option"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('template')

    @setup({'template': '{% load i18n %}{% trans "Yes" noop noop %}'})
    def test_syntax_error_duplicate_option(self):
        msg = "The 'noop' option was specified more than once."
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            self.engine.render_to_string('template')

    @setup({'template': '{% load i18n %}{% trans "%s" %}'})
    def test_trans_tag_using_a_string_that_looks_like_str_fmt(self):
        output = self.engine.render_to_string('template')
        self.assertEqual(output, '%s')


class TranslationTransTagTests(SimpleTestCase):

    @override_settings(LOCALE_PATHS=extended_locale_paths)
    def test_template_tags_pgettext(self):
        """{% trans %} takes message contexts into account (#14806)."""
        trans_real._active = local()
        trans_real._translations = {}
        with translation.override('de'):
            # Nonexistent context...
            t = Template('{% load i18n %}{% trans "May" context "nonexistent" %}')
            rendered = t.render(Context())
            self.assertEqual(rendered, 'May')

            # Existing context... using a literal
            t = Template('{% load i18n %}{% trans "May" context "month name" %}')
            rendered = t.render(Context())
            self.assertEqual(rendered, 'Mai')
            t = Template('{% load i18n %}{% trans "May" context "verb" %}')
            rendered = t.render(Context())
            self.assertEqual(rendered, 'Kann')

            # Using a variable
            t = Template('{% load i18n %}{% trans "May" context message_context %}')
            rendered = t.render(Context({'message_context': 'month name'}))
            self.assertEqual(rendered, 'Mai')
            t = Template('{% load i18n %}{% trans "May" context message_context %}')
            rendered = t.render(Context({'message_context': 'verb'}))
            self.assertEqual(rendered, 'Kann')

            # Using a filter
            t = Template('{% load i18n %}{% trans "May" context message_context|lower %}')
            rendered = t.render(Context({'message_context': 'MONTH NAME'}))
            self.assertEqual(rendered, 'Mai')
            t = Template('{% load i18n %}{% trans "May" context message_context|lower %}')
            rendered = t.render(Context({'message_context': 'VERB'}))
            self.assertEqual(rendered, 'Kann')

            # Using 'as'
            t = Template('{% load i18n %}{% trans "May" context "month name" as var %}Value: {{ var }}')
            rendered = t.render(Context())
            self.assertEqual(rendered, 'Value: Mai')
            t = Template('{% load i18n %}{% trans "May" as var context "verb" %}Value: {{ var }}')
            rendered = t.render(Context())
            self.assertEqual(rendered, 'Value: Kann')


class MultipleLocaleActivationTransTagTests(MultipleLocaleActivationTestCase):

    def test_single_locale_activation(self):
        """
        Simple baseline behavior with one locale for all the supported i18n
        constructs.
        """
        with translation.override('fr'):
            self.assertEqual(Template("{% load i18n %}{% trans 'Yes' %}").render(Context({})), 'Oui')

    def test_multiple_locale_trans(self):
        with translation.override('de'):
            t = Template("{% load i18n %}{% trans 'No' %}")
        with translation.override(self._old_language), translation.override('nl'):
            self.assertEqual(t.render(Context({})), 'Nee')

    def test_multiple_locale_deactivate_trans(self):
        with translation.override('de', deactivate=True):
            t = Template("{% load i18n %}{% trans 'No' %}")
        with translation.override('nl'):
            self.assertEqual(t.render(Context({})), 'Nee')

    def test_multiple_locale_direct_switch_trans(self):
        with translation.override('de'):
            t = Template("{% load i18n %}{% trans 'No' %}")
        with translation.override('nl'):
            self.assertEqual(t.render(Context({})), 'Nee')
