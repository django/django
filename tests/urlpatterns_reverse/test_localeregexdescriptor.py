import os
from pathlib import Path
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
from django.urls.resolvers import LocaleRegexDescriptor, RegexPattern
from django.utils import translation

here = os.path.dirname(os.path.abspath(__file__))


@override_settings(LOCALE_PATHS=[os.path.join(here, "translations", "locale")])
class LocaleRegexDescriptorTests(SimpleTestCase):
    def setUp(self):
        translation.trans_real._translations = {}

    def tearDown(self):
        translation.trans_real._translations = {}

    def test_translated_regex_compiled_per_language(self):
        provider = RegexPattern(translation.gettext_lazy("^foo/$"))
        with translation.override("de"):
            de_compiled = provider.regex
            # compiled only once per language
            error = AssertionError(
                "tried to compile url regex twice for the same language"
            )
            with mock.patch("django.urls.resolvers.re.compile", side_effect=error):
                de_compiled_2 = provider.regex
        with translation.override("fr"):
            fr_compiled = provider.regex
        self.assertEqual(fr_compiled.pattern, "^foo-fr/$")
        self.assertEqual(de_compiled.pattern, "^foo-de/$")
        self.assertEqual(de_compiled, de_compiled_2)

    def test_nontranslated_regex_compiled_once(self):
        provider = RegexPattern("^foo/$")
        with translation.override("de"):
            de_compiled = provider.regex
        with translation.override("fr"):
            # compiled only once, regardless of language
            error = AssertionError("tried to compile non-translated url regex twice")
            with mock.patch("django.urls.resolvers.re.compile", side_effect=error):
                fr_compiled = provider.regex
        self.assertEqual(de_compiled.pattern, "^foo/$")
        self.assertEqual(fr_compiled.pattern, "^foo/$")

    def test_regex_compile_error(self):
        """Regex errors are re-raised as ImproperlyConfigured."""
        provider = RegexPattern("*")
        msg = '"*" is not a valid regular expression: nothing to repeat'
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            provider.regex

    def test_access_locale_regex_descriptor(self):
        self.assertIsInstance(RegexPattern.regex, LocaleRegexDescriptor)


@override_settings(LOCALE_PATHS=[Path(here) / "translations" / "locale"])
class LocaleRegexDescriptorPathLibTests(LocaleRegexDescriptorTests):
    pass
