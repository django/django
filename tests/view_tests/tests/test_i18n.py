# -*- coding:utf-8 -*-
import gettext
import json
import os
import unittest
from os import path

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import (
    LiveServerTestCase, TestCase, modify_settings, override_settings,
)
from django.utils import six
from django.utils._os import upath
from django.utils.module_loading import import_string
from django.utils.translation import LANGUAGE_SESSION_KEY, override

from ..urls import locale_dir


@override_settings(ROOT_URLCONF='view_tests.urls')
class I18NTests(TestCase):
    """ Tests django views in django/views/i18n.py """

    def test_setlang(self):
        """
        The set_language view can be used to change the session language.

        The user is redirected to the 'next' argument if provided.
        """
        for lang_code, lang_name in settings.LANGUAGES:
            post_data = dict(language=lang_code, next='/')
            response = self.client.post('/i18n/setlang/', data=post_data)
            self.assertRedirects(response, 'http://testserver/')
            self.assertEqual(self.client.session[LANGUAGE_SESSION_KEY], lang_code)

    def test_setlang_unsafe_next(self):
        """
        The set_language view only redirects to the 'next' argument if it is
        "safe".
        """
        lang_code, lang_name = settings.LANGUAGES[0]
        post_data = dict(language=lang_code, next='//unsafe/redirection/')
        response = self.client.post('/i18n/setlang/', data=post_data)
        self.assertEqual(response.url, 'http://testserver/')
        self.assertEqual(self.client.session[LANGUAGE_SESSION_KEY], lang_code)

    def test_setlang_reversal(self):
        self.assertEqual(reverse('set_language'), '/i18n/setlang/')

    def test_setlang_cookie(self):
        # we force saving language to a cookie rather than a session
        # by excluding session middleware and those which do require it
        test_settings = dict(
            MIDDLEWARE_CLASSES=('django.middleware.common.CommonMiddleware',),
            LANGUAGE_COOKIE_NAME='mylanguage',
            LANGUAGE_COOKIE_AGE=3600 * 7 * 2,
            LANGUAGE_COOKIE_DOMAIN='.example.com',
            LANGUAGE_COOKIE_PATH='/test/',
        )
        with self.settings(**test_settings):
            post_data = dict(language='pl', next='/views/')
            response = self.client.post('/i18n/setlang/', data=post_data)
            language_cookie = response.cookies.get('mylanguage')
            self.assertEqual(language_cookie.value, 'pl')
            self.assertEqual(language_cookie['domain'], '.example.com')
            self.assertEqual(language_cookie['path'], '/test/')
            self.assertEqual(language_cookie['max-age'], 3600 * 7 * 2)

    def test_jsi18n(self):
        """The javascript_catalog can be deployed with language settings"""
        for lang_code in ['es', 'fr', 'ru']:
            with override(lang_code):
                catalog = gettext.translation('djangojs', locale_dir, [lang_code])
                if six.PY3:
                    trans_txt = catalog.gettext('this is to be translated')
                else:
                    trans_txt = catalog.ugettext('this is to be translated')
                response = self.client.get('/jsi18n/')
                # response content must include a line like:
                # "this is to be translated": <value of trans_txt Python variable>
                # json.dumps() is used to be able to check unicode strings
                self.assertContains(response, json.dumps(trans_txt), 1)
                if lang_code == 'fr':
                    # Message with context (msgctxt)
                    self.assertContains(response, r'"month name\u0004May": "mai"', 1)


@override_settings(ROOT_URLCONF='view_tests.urls')
class JsI18NTests(TestCase):
    """
    Tests django views in django/views/i18n.py that need to change
    settings.LANGUAGE_CODE.
    """

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
            response = self.client.get('/jsi18n/')
            self.assertNotContains(response, 'esto tiene que ser traducido')

    def test_jsi18n_fallback_language(self):
        """
        Let's make sure that the fallback language is still working properly
        in cases where the selected language cannot be found.
        """
        with self.settings(LANGUAGE_CODE='fr'), override('fi'):
            response = self.client.get('/jsi18n/')
            self.assertContains(response, 'il faut le traduire')

    def test_i18n_language_non_english_default(self):
        """
        Check if the Javascript i18n view returns an empty language catalog
        if the default language is non-English, the selected language
        is English and there is not 'en' translation available. See #13388,
        #3594 and #13726 for more details.
        """
        with self.settings(LANGUAGE_CODE='fr'), override('en-us'):
            response = self.client.get('/jsi18n/')
            self.assertNotContains(response, 'Choisir une heure')

    @modify_settings(INSTALLED_APPS={'append': 'view_tests.app0'})
    def test_non_english_default_english_userpref(self):
        """
        Same as above with the difference that there IS an 'en' translation
        available. The Javascript i18n view must return a NON empty language catalog
        with the proper English translations. See #13726 for more details.
        """
        with self.settings(LANGUAGE_CODE='fr'), override('en-us'):
            response = self.client.get('/jsi18n_english_translation/')
            self.assertContains(response, 'this app0 string is to be translated')

    def test_i18n_language_non_english_fallback(self):
        """
        Makes sure that the fallback language is still working properly
        in cases where the selected language cannot be found.
        """
        with self.settings(LANGUAGE_CODE='fr'), override('none'):
            response = self.client.get('/jsi18n/')
            self.assertContains(response, 'Choisir une heure')

    def test_escaping(self):
        # Force a language via GET otherwise the gettext functions are a noop!
        response = self.client.get('/jsi18n_admin/?language=de')
        self.assertContains(response, '\\x04')

    @modify_settings(INSTALLED_APPS={'append': ['view_tests.app5']})
    def test_non_BMP_char(self):
        """
        Non-BMP characters should not break the javascript_catalog (#21725).
        """
        with self.settings(LANGUAGE_CODE='en-us'), override('fr'):
            response = self.client.get('/jsi18n/app5/')
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'emoji')
            self.assertContains(response, '\\ud83d\\udca9')


@override_settings(ROOT_URLCONF='view_tests.urls')
class JsI18NTestsMultiPackage(TestCase):
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
            response = self.client.get('/jsi18n_multi_packages1/')
            self.assertContains(response, 'il faut traduire cette cha\\u00eene de caract\\u00e8res de app1')

    @modify_settings(INSTALLED_APPS={'append': ['view_tests.app3', 'view_tests.app4']})
    def test_i18n_different_non_english_languages(self):
        """
        Similar to above but with neither default or requested language being
        English.
        """
        with self.settings(LANGUAGE_CODE='fr'), override('es-ar'):
            response = self.client.get('/jsi18n_multi_packages2/')
            self.assertContains(response, 'este texto de app3 debe ser traducido')

    def test_i18n_with_locale_paths(self):
        extended_locale_paths = settings.LOCALE_PATHS + (
            path.join(path.dirname(
                path.dirname(path.abspath(upath(__file__)))), 'app3', 'locale'),)
        with self.settings(LANGUAGE_CODE='es-ar', LOCALE_PATHS=extended_locale_paths):
            with override('es-ar'):
                response = self.client.get('/jsi18n/')
                self.assertContains(response,
                    'este texto de app3 debe ser traducido')


skip_selenium = not os.environ.get('DJANGO_SELENIUM_TESTS', False)


@unittest.skipIf(skip_selenium, 'Selenium tests not requested')
@override_settings(ROOT_URLCONF='view_tests.urls')
class JavascriptI18nTests(LiveServerTestCase):

    # The test cases use fixtures & translations from these apps.
    available_apps = [
        'django.contrib.admin', 'django.contrib.auth',
        'django.contrib.contenttypes', 'view_tests',
    ]
    webdriver_class = 'selenium.webdriver.firefox.webdriver.WebDriver'

    @classmethod
    def setUpClass(cls):
        try:
            cls.selenium = import_string(cls.webdriver_class)()
        except Exception as e:
            raise unittest.SkipTest('Selenium webdriver "%s" not installed or '
                                    'not operational: %s' % (cls.webdriver_class, str(e)))
        super(JavascriptI18nTests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(JavascriptI18nTests, cls).tearDownClass()

    @override_settings(LANGUAGE_CODE='de')
    def test_javascript_gettext(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/jsi18n_template/'))

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


class JavascriptI18nChromeTests(JavascriptI18nTests):
    webdriver_class = 'selenium.webdriver.chrome.webdriver.WebDriver'


class JavascriptI18nIETests(JavascriptI18nTests):
    webdriver_class = 'selenium.webdriver.ie.webdriver.WebDriver'
