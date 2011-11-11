# -*- coding:utf-8 -*-
from __future__ import with_statement, absolute_import

import gettext
from os import path

from django.conf import settings
from django.test import TestCase
from django.utils.translation import override, activate, get_language
from django.utils.text import javascript_quote

from ..urls import locale_dir


class I18NTests(TestCase):
    """ Tests django views in django/views/i18n.py """

    def test_setlang(self):
        """The set_language view can be used to change the session language"""
        for lang_code, lang_name in settings.LANGUAGES:
            post_data = dict(language=lang_code, next='/views/')
            response = self.client.post('/views/i18n/setlang/', data=post_data)
            self.assertRedirects(response, 'http://testserver/views/')
            self.assertEqual(self.client.session['django_language'], lang_code)

    def test_jsi18n(self):
        """The javascript_catalog can be deployed with language settings"""
        saved_lang = get_language()
        for lang_code in ['es', 'fr', 'ru']:
            activate(lang_code)
            catalog = gettext.translation('djangojs', locale_dir, [lang_code])
            trans_txt = catalog.ugettext('this is to be translated')
            response = self.client.get('/views/jsi18n/')
            # in response content must to be a line like that:
            # catalog['this is to be translated'] = 'same_that_trans_txt'
            # javascript_quote is used to be able to check unicode strings
            self.assertContains(response, javascript_quote(trans_txt), 1)
            if lang_code == 'fr':
                # Message with context (msgctxt)
                self.assertContains(response, "['month name\x04May'] = 'mai';", 1)
        activate(saved_lang)


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
        with self.settings(LANGUAGE_CODE='es'):
            with override('en-us'):
                response = self.client.get('/views/jsi18n/')
                self.assertNotContains(response, 'esto tiene que ser traducido')

    def test_jsi18n_fallback_language(self):
        """
        Let's make sure that the fallback language is still working properly
        in cases where the selected language cannot be found.
        """
        with self.settings(LANGUAGE_CODE='fr'):
            with override('fi'):
                response = self.client.get('/views/jsi18n/')
                self.assertContains(response, 'il faut le traduire')

    def testI18NLanguageNonEnglishDefault(self):
        """
        Check if the Javascript i18n view returns an empty language catalog
        if the default language is non-English, the selected language
        is English and there is not 'en' translation available. See #13388,
        #3594 and #13726 for more details.
        """
        with self.settings(LANGUAGE_CODE='fr'):
            with override('en-us'):
                response = self.client.get('/views/jsi18n/')
                self.assertNotContains(response, 'Choisir une heure')

    def test_nonenglish_default_english_userpref(self):
        """
        Same as above with the difference that there IS an 'en' translation
        available. The Javascript i18n view must return a NON empty language catalog
        with the proper English translations. See #13726 for more details.
        """
        extended_apps = list(settings.INSTALLED_APPS) + ['regressiontests.views.app0']
        with self.settings(LANGUAGE_CODE='fr', INSTALLED_APPS=extended_apps):
            with override('en-us'):
                response = self.client.get('/views/jsi18n_english_translation/')
                self.assertContains(response, javascript_quote('this app0 string is to be translated'))

    def testI18NLanguageNonEnglishFallback(self):
        """
        Makes sure that the fallback language is still working properly
        in cases where the selected language cannot be found.
        """
        with self.settings(LANGUAGE_CODE='fr'):
            with override('none'):
                response = self.client.get('/views/jsi18n/')
                self.assertContains(response, 'Choisir une heure')


class JsI18NTestsMultiPackage(TestCase):
    """
    Tests for django views in django/views/i18n.py that need to change
    settings.LANGUAGE_CODE and merge JS translation from several packages.
    """
    def testI18NLanguageEnglishDefault(self):
        """
        Check if the JavaScript i18n view returns a complete language catalog
        if the default language is en-us, the selected language has a
        translation available and a catalog composed by djangojs domain
        translations of multiple Python packages is requested. See #13388,
        #3594 and #13514 for more details.
        """
        extended_apps = list(settings.INSTALLED_APPS) + ['regressiontests.views.app1', 'regressiontests.views.app2']
        with self.settings(LANGUAGE_CODE='en-us', INSTALLED_APPS=extended_apps):
            with override('fr'):
                response = self.client.get('/views/jsi18n_multi_packages1/')
                self.assertContains(response, javascript_quote('il faut traduire cette chaîne de caractères de app1'))

    def testI18NDifferentNonEnLangs(self):
        """
        Similar to above but with neither default or requested language being
        English.
        """
        extended_apps = list(settings.INSTALLED_APPS) + ['regressiontests.views.app3', 'regressiontests.views.app4']
        with self.settings(LANGUAGE_CODE='fr', INSTALLED_APPS=extended_apps):
            with override('es-ar'):
                response = self.client.get('/views/jsi18n_multi_packages2/')
                self.assertContains(response, javascript_quote('este texto de app3 debe ser traducido'))

    def testI18NWithLocalePaths(self):
        extended_locale_paths = settings.LOCALE_PATHS + (
            path.join(path.dirname(
                path.dirname(path.abspath(__file__))), 'app3', 'locale'),)
        with self.settings(LANGUAGE_CODE='es-ar', LOCALE_PATHS=extended_locale_paths):
            with override('es-ar'):
                response = self.client.get('/views/jsi18n/')
                self.assertContains(response,
                    javascript_quote('este texto de app3 debe ser traducido'))
