# -*- coding:utf-8 -*-
from __future__ import unicode_literals

import gettext
import json
from os import path

from django.conf import settings
from django.test import (
    SimpleTestCase, ignore_warnings, modify_settings, override_settings,
)
from django.test.selenium import SeleniumTestCase
from django.utils import six
from django.utils._os import upath
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.translation import override

from ..urls import locale_dir


@override_settings(ROOT_URLCONF='view_tests.urls')
@ignore_warnings(category=RemovedInDjango20Warning)
class JsI18NTests(SimpleTestCase):
    """
    Tests deprecated django views in django/views/i18n.py
    """
    def test_jsi18n(self):
        """The javascript_catalog can be deployed with language settings"""
        for lang_code in ['es', 'fr', 'ru']:
            with override(lang_code):
                catalog = gettext.translation('djangojs', locale_dir, [lang_code])
                if six.PY3:
                    trans_txt = catalog.gettext('this is to be translated')
                else:
                    trans_txt = catalog.ugettext('this is to be translated')
                response = self.client.get('/old_jsi18n/')
                # response content must include a line like:
                # "this is to be translated": <value of trans_txt Python variable>
                # json.dumps() is used to be able to check unicode strings
                self.assertContains(response, json.dumps(trans_txt), 1)
                if lang_code == 'fr':
                    # Message with context (msgctxt)
                    self.assertContains(response, '"month name\\u0004May": "mai"', 1)

    def test_jsoni18n(self):
        """
        The json_catalog returns the language catalog and settings as JSON.
        """
        with override('de'):
            response = self.client.get('/old_jsoni18n/')
            data = json.loads(response.content.decode('utf-8'))
            self.assertIn('catalog', data)
            self.assertIn('formats', data)
            self.assertIn('plural', data)
            self.assertEqual(data['catalog']['month name\x04May'], 'Mai')
            self.assertIn('DATETIME_FORMAT', data['formats'])
            self.assertEqual(data['plural'], '(n != 1)')

    def test_jsi18n_with_missing_en_files(self):
        """
        The javascript_catalog shouldn't load the fallback language in the
        case that the current selected language is actually the one translated
        from, and hence missing translation files completely.

        This happens easily when you're translating from English to other
        languages and you've set settings.LANGUAGE_CODE to some other language
        than English.
        """
        with self.settings(LANGUAGE_CODE='es'), override('en-us'):
            response = self.client.get('/old_jsi18n/')
            self.assertNotContains(response, 'esto tiene que ser traducido')

    def test_jsoni18n_with_missing_en_files(self):
        """
        Same as above for the json_catalog view. Here we also check for the
        expected JSON format.
        """
        with self.settings(LANGUAGE_CODE='es'), override('en-us'):
            response = self.client.get('/old_jsoni18n/')
            data = json.loads(response.content.decode('utf-8'))
            self.assertIn('catalog', data)
            self.assertIn('formats', data)
            self.assertIn('plural', data)
            self.assertEqual(data['catalog'], {})
            self.assertIn('DATETIME_FORMAT', data['formats'])
            self.assertIsNone(data['plural'])

    def test_jsi18n_fallback_language(self):
        """
        Let's make sure that the fallback language is still working properly
        in cases where the selected language cannot be found.
        """
        with self.settings(LANGUAGE_CODE='fr'), override('fi'):
            response = self.client.get('/old_jsi18n/')
            self.assertContains(response, 'il faut le traduire')
            self.assertNotContains(response, "Untranslated string")

    def test_i18n_fallback_language_plural(self):
        """
        The fallback to a language with less plural forms maintains the real
        language's number of plural forms.
        """
        with self.settings(LANGUAGE_CODE='pt'), override('ru'):
            response = self.client.get('/jsi18n/')
            self.assertEqual(
                response.context['catalog']['{count} plural3'],
                ['{count} plural3', '{count} plural3s', '{count} plural3 p3t']
            )

    def test_i18n_english_variant(self):
        with override('en-gb'):
            response = self.client.get('/old_jsi18n/')
            self.assertIn(
                '"this color is to be translated": "this colour is to be translated"',
                response.context['catalog_str']
            )

    def test_i18n_language_non_english_default(self):
        """
        Check if the Javascript i18n view returns an empty language catalog
        if the default language is non-English, the selected language
        is English and there is not 'en' translation available. See #13388,
        #3594 and #13726 for more details.
        """
        with self.settings(LANGUAGE_CODE='fr'), override('en-us'):
            response = self.client.get('/old_jsi18n/')
            self.assertNotContains(response, 'Choisir une heure')

    @modify_settings(INSTALLED_APPS={'append': 'view_tests.app0'})
    def test_non_english_default_english_userpref(self):
        """
        Same as above with the difference that there IS an 'en' translation
        available. The Javascript i18n view must return a NON empty language catalog
        with the proper English translations. See #13726 for more details.
        """
        with self.settings(LANGUAGE_CODE='fr'), override('en-us'):
            response = self.client.get('/old_jsi18n_english_translation/')
            self.assertContains(response, 'this app0 string is to be translated')

    def test_i18n_language_non_english_fallback(self):
        """
        Makes sure that the fallback language is still working properly
        in cases where the selected language cannot be found.
        """
        with self.settings(LANGUAGE_CODE='fr'), override('none'):
            response = self.client.get('/old_jsi18n/')
            self.assertContains(response, 'Choisir une heure')

    def test_escaping(self):
        # Force a language via GET otherwise the gettext functions are a noop!
        response = self.client.get('/old_jsi18n_admin/?language=de')
        self.assertContains(response, '\\x04')

    @modify_settings(INSTALLED_APPS={'append': ['view_tests.app5']})
    def test_non_BMP_char(self):
        """
        Non-BMP characters should not break the javascript_catalog (#21725).
        """
        with self.settings(LANGUAGE_CODE='en-us'), override('fr'):
            response = self.client.get('/old_jsi18n/app5/')
            self.assertContains(response, 'emoji')
            self.assertContains(response, '\\ud83d\\udca9')


@override_settings(ROOT_URLCONF='view_tests.urls')
@ignore_warnings(category=RemovedInDjango20Warning)
class JsI18NTestsMultiPackage(SimpleTestCase):
    """
    Tests for django views in django/views/i18n.py that need to change
    settings.LANGUAGE_CODE and merge JS translation from several packages.
    """
    @modify_settings(INSTALLED_APPS={'append': ['view_tests.app1', 'view_tests.app2']})
    def test_i18n_language_english_default(self):
        """
        Check if the JavaScript i18n view returns a complete language catalog
        if the default language is en-us, the selected language has a
        translation available and a catalog composed by djangojs domain
        translations of multiple Python packages is requested. See #13388,
        #3594 and #13514 for more details.
        """
        with self.settings(LANGUAGE_CODE='en-us'), override('fr'):
            response = self.client.get('/old_jsi18n_multi_packages1/')
            self.assertContains(response, 'il faut traduire cette cha\\u00eene de caract\\u00e8res de app1')

    @modify_settings(INSTALLED_APPS={'append': ['view_tests.app3', 'view_tests.app4']})
    def test_i18n_different_non_english_languages(self):
        """
        Similar to above but with neither default or requested language being
        English.
        """
        with self.settings(LANGUAGE_CODE='fr'), override('es-ar'):
            response = self.client.get('/old_jsi18n_multi_packages2/')
            self.assertContains(response, 'este texto de app3 debe ser traducido')

    def test_i18n_with_locale_paths(self):
        extended_locale_paths = settings.LOCALE_PATHS + [
            path.join(
                path.dirname(path.dirname(path.abspath(upath(__file__)))),
                'app3',
                'locale',
            ),
        ]
        with self.settings(LANGUAGE_CODE='es-ar', LOCALE_PATHS=extended_locale_paths):
            with override('es-ar'):
                response = self.client.get('/old_jsi18n/')
                self.assertContains(response, 'este texto de app3 debe ser traducido')


@override_settings(ROOT_URLCONF='view_tests.urls')
@ignore_warnings(category=RemovedInDjango20Warning)
class JavascriptI18nTests(SeleniumTestCase):

    # The test cases use fixtures & translations from these apps.
    available_apps = [
        'django.contrib.admin', 'django.contrib.auth',
        'django.contrib.contenttypes', 'view_tests',
    ]

    @override_settings(LANGUAGE_CODE='de')
    def test_javascript_gettext(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/old_jsi18n_template/'))

        elem = self.selenium.find_element_by_id("gettext")
        self.assertEqual(elem.text, "Entfernen")
        elem = self.selenium.find_element_by_id("ngettext_sing")
        self.assertEqual(elem.text, "1 Element")
        elem = self.selenium.find_element_by_id("ngettext_plur")
        self.assertEqual(elem.text, "455 Elemente")
        elem = self.selenium.find_element_by_id("pgettext")
        self.assertEqual(elem.text, "Kann")
        elem = self.selenium.find_element_by_id("npgettext_sing")
        self.assertEqual(elem.text, "1 Resultat")
        elem = self.selenium.find_element_by_id("npgettext_plur")
        self.assertEqual(elem.text, "455 Resultate")

    @modify_settings(INSTALLED_APPS={'append': ['view_tests.app1', 'view_tests.app2']})
    @override_settings(LANGUAGE_CODE='fr')
    def test_multiple_catalogs(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/old_jsi18n_multi_catalogs/'))

        elem = self.selenium.find_element_by_id('app1string')
        self.assertEqual(elem.text, 'il faut traduire cette chaîne de caractères de app1')
        elem = self.selenium.find_element_by_id('app2string')
        self.assertEqual(elem.text, 'il faut traduire cette chaîne de caractères de app2')
