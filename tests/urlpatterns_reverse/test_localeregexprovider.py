import os

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, mock, override_settings
from django.urls import LocaleRegexProvider
from django.urls.resolvers import LocaleRegexDescriptor
from django.utils import translation
from django.utils._os import upath

here = os.path.dirname(upath(os.path.abspath(__file__)))


@override_settings(LOCALE_PATHS=[os.path.join(here, 'translations', 'locale')])
class LocaleRegexProviderTests(SimpleTestCase):
    def setUp(self):
        translation.trans_real._translations = {}

    def tearDown(self):
        translation.trans_real._translations = {}

    def test_translated_regex_compiled_per_language(self):
        provider = LocaleRegexProvider(translation.gettext_lazy('^foo/$'))
        with translation.override('de'):
            de_compiled = provider.regex
            # compiled only once per language
            error = AssertionError('tried to compile url regex twice for the same language')
            with mock.patch('django.urls.resolvers.re.compile', side_effect=error):
                de_compiled_2 = provider.regex
        with translation.override('fr'):
            fr_compiled = provider.regex
        self.assertEqual(fr_compiled.pattern, '^foo-fr/$')
        self.assertEqual(de_compiled.pattern, '^foo-de/$')
        self.assertEqual(de_compiled, de_compiled_2)

    def test_nontranslated_regex_compiled_once(self):
        provider = LocaleRegexProvider('^foo/$')
        with translation.override('de'):
            de_compiled = provider.regex
        with translation.override('fr'):
            # compiled only once, regardless of language
            error = AssertionError('tried to compile non-translated url regex twice')
            with mock.patch('django.urls.resolvers.re.compile', side_effect=error):
                fr_compiled = provider.regex
        self.assertEqual(de_compiled.pattern, '^foo/$')
        self.assertEqual(fr_compiled.pattern, '^foo/$')

    def test_regex_compile_error(self):
        """Regex errors are re-raised as ImproperlyConfigured."""
        provider = LocaleRegexProvider('*')
        msg = '"*" is not a valid regular expression: nothing to repeat'
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            provider.regex

    def test_access_locale_regex_descriptor(self):
        self.assertIsInstance(LocaleRegexProvider.regex, LocaleRegexDescriptor)
