import gettext
import json
from os import path

from django.conf import settings
from django.test import (
    RequestFactory, SimpleTestCase, TestCase, ignore_warnings, modify_settings,
    override_settings,
)
from django.test.selenium import SeleniumTestCase
from django.urls import reverse
from django.utils.deprecation import RemovedInDjango40Warning
from django.utils.translation import (
    LANGUAGE_SESSION_KEY, get_language, override,
)
from django.views.i18n import JavaScriptCatalog, get_formats

from ..urls import locale_dir


@override_settings(ROOT_URLCONF='view_tests.urls')
class SetLanguageTests(TestCase):
    """Test the django.views.i18n.set_language view."""

    def _get_inactive_language_code(self):
        """Return language code for a language which is not activated."""
        current_language = get_language()
        return [code for code, name in settings.LANGUAGES if not code == current_language][0]

    def test_setlang(self):
        """
        The set_language view can be used to change the session language.

        The user is redirected to the 'next' argument if provided.
        """
        lang_code = self._get_inactive_language_code()
        post_data = {'language': lang_code, 'next': '/'}
        response = self.client.post('/i18n/setlang/', post_data, HTTP_REFERER='/i_should_not_be_used/')
        self.assertRedirects(response, '/')
        with ignore_warnings(category=RemovedInDjango40Warning):
            self.assertEqual(self.client.session[LANGUAGE_SESSION_KEY], lang_code)
        # The language is set in a cookie.
        language_cookie = self.client.cookies[settings.LANGUAGE_COOKIE_NAME]
        self.assertEqual(language_cookie.value, lang_code)
        self.assertEqual(language_cookie['domain'], '')
        self.assertEqual(language_cookie['path'], '/')
        self.assertEqual(language_cookie['max-age'], '')
        self.assertEqual(language_cookie['httponly'], '')
        self.assertEqual(language_cookie['samesite'], '')
        self.assertEqual(language_cookie['secure'], '')

    def test_setlang_unsafe_next(self):
        """
        The set_language view only redirects to the 'next' argument if it is
        "safe".
        """
        lang_code = self._get_inactive_language_code()
        post_data = {'language': lang_code, 'next': '//unsafe/redirection/'}
        response = self.client.post('/i18n/setlang/', data=post_data)
        self.assertEqual(response.url, '/')
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, lang_code)
        with ignore_warnings(category=RemovedInDjango40Warning):
            self.assertEqual(self.client.session[LANGUAGE_SESSION_KEY], lang_code)

    def test_setlang_http_next(self):
        """
        The set_language view only redirects to the 'next' argument if it is
        "safe" and its scheme is https if the request was sent over https.
        """
        lang_code = self._get_inactive_language_code()
        non_https_next_url = 'http://testserver/redirection/'
        post_data = {'language': lang_code, 'next': non_https_next_url}
        # Insecure URL in POST data.
        response = self.client.post('/i18n/setlang/', data=post_data, secure=True)
        self.assertEqual(response.url, '/')
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, lang_code)
        with ignore_warnings(category=RemovedInDjango40Warning):
            self.assertEqual(self.client.session[LANGUAGE_SESSION_KEY], lang_code)
        # Insecure URL in HTTP referer.
        response = self.client.post('/i18n/setlang/', secure=True, HTTP_REFERER=non_https_next_url)
        self.assertEqual(response.url, '/')
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, lang_code)
        with ignore_warnings(category=RemovedInDjango40Warning):
            self.assertEqual(self.client.session[LANGUAGE_SESSION_KEY], lang_code)

    def test_setlang_redirect_to_referer(self):
        """
        The set_language view redirects to the URL in the referer header when
        there isn't a "next" parameter.
        """
        lang_code = self._get_inactive_language_code()
        post_data = {'language': lang_code}
        response = self.client.post('/i18n/setlang/', post_data, HTTP_REFERER='/i18n/')
        self.assertRedirects(response, '/i18n/', fetch_redirect_response=False)
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, lang_code)
        with ignore_warnings(category=RemovedInDjango40Warning):
            self.assertEqual(self.client.session[LANGUAGE_SESSION_KEY], lang_code)

    def test_setlang_default_redirect(self):
        """
        The set_language view redirects to '/' when there isn't a referer or
        "next" parameter.
        """
        lang_code = self._get_inactive_language_code()
        post_data = {'language': lang_code}
        response = self.client.post('/i18n/setlang/', post_data)
        self.assertRedirects(response, '/')
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, lang_code)
        with ignore_warnings(category=RemovedInDjango40Warning):
            self.assertEqual(self.client.session[LANGUAGE_SESSION_KEY], lang_code)

    def test_setlang_performs_redirect_for_ajax_if_explicitly_requested(self):
        """
        The set_language view redirects to the "next" parameter for requests
        not accepting HTML response content.
        """
        lang_code = self._get_inactive_language_code()
        post_data = {'language': lang_code, 'next': '/'}
        response = self.client.post('/i18n/setlang/', post_data, HTTP_ACCEPT='application/json')
        self.assertRedirects(response, '/')
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, lang_code)
        with ignore_warnings(category=RemovedInDjango40Warning):
            self.assertEqual(self.client.session[LANGUAGE_SESSION_KEY], lang_code)

    def test_setlang_doesnt_perform_a_redirect_to_referer_for_ajax(self):
        """
        The set_language view doesn't redirect to the HTTP referer header if
        the request doesn't accept HTML response content.
        """
        lang_code = self._get_inactive_language_code()
        post_data = {'language': lang_code}
        headers = {'HTTP_REFERER': '/', 'HTTP_ACCEPT': 'application/json'}
        response = self.client.post('/i18n/setlang/', post_data, **headers)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, lang_code)
        with ignore_warnings(category=RemovedInDjango40Warning):
            self.assertEqual(self.client.session[LANGUAGE_SESSION_KEY], lang_code)

    def test_setlang_doesnt_perform_a_default_redirect_for_ajax(self):
        """
        The set_language view returns 204 by default for requests not accepting
        HTML response content.
        """
        lang_code = self._get_inactive_language_code()
        post_data = {'language': lang_code}
        response = self.client.post('/i18n/setlang/', post_data, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, lang_code)
        with ignore_warnings(category=RemovedInDjango40Warning):
            self.assertEqual(self.client.session[LANGUAGE_SESSION_KEY], lang_code)

    def test_setlang_unsafe_next_for_ajax(self):
        """
        The fallback to root URL for the set_language view works for requests
        not accepting HTML response content.
        """
        lang_code = self._get_inactive_language_code()
        post_data = {'language': lang_code, 'next': '//unsafe/redirection/'}
        response = self.client.post('/i18n/setlang/', post_data, HTTP_ACCEPT='application/json')
        self.assertEqual(response.url, '/')
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, lang_code)

    def test_session_language_deprecation(self):
        msg = (
            'The user language will no longer be stored in request.session '
            'in Django 4.0. Read it from '
            'request.COOKIES[settings.LANGUAGE_COOKIE_NAME] instead.'
        )
        with self.assertRaisesMessage(RemovedInDjango40Warning, msg):
            self.client.session[LANGUAGE_SESSION_KEY]

    def test_setlang_reversal(self):
        self.assertEqual(reverse('set_language'), '/i18n/setlang/')

    def test_setlang_cookie(self):
        # we force saving language to a cookie rather than a session
        # by excluding session middleware and those which do require it
        test_settings = {
            'MIDDLEWARE': ['django.middleware.common.CommonMiddleware'],
            'LANGUAGE_COOKIE_NAME': 'mylanguage',
            'LANGUAGE_COOKIE_AGE': 3600 * 7 * 2,
            'LANGUAGE_COOKIE_DOMAIN': '.example.com',
            'LANGUAGE_COOKIE_PATH': '/test/',
            'LANGUAGE_COOKIE_HTTPONLY': True,
            'LANGUAGE_COOKIE_SAMESITE': 'Strict',
            'LANGUAGE_COOKIE_SECURE': True,
        }
        with self.settings(**test_settings):
            post_data = {'language': 'pl', 'next': '/views/'}
            response = self.client.post('/i18n/setlang/', data=post_data)
            language_cookie = response.cookies.get('mylanguage')
            self.assertEqual(language_cookie.value, 'pl')
            self.assertEqual(language_cookie['domain'], '.example.com')
            self.assertEqual(language_cookie['path'], '/test/')
            self.assertEqual(language_cookie['max-age'], 3600 * 7 * 2)
            self.assertIs(language_cookie['httponly'], True)
            self.assertEqual(language_cookie['samesite'], 'Strict')
            self.assertIs(language_cookie['secure'], True)

    def test_setlang_decodes_http_referer_url(self):
        """
        The set_language view decodes the HTTP_REFERER URL.
        """
        # The URL & view must exist for this to work as a regression test.
        self.assertEqual(reverse('with_parameter', kwargs={'parameter': 'x'}), '/test-setlang/x/')
        lang_code = self._get_inactive_language_code()
        encoded_url = '/test-setlang/%C3%A4/'  # (%C3%A4 decodes to ä)
        response = self.client.post('/i18n/setlang/', {'language': lang_code}, HTTP_REFERER=encoded_url)
        self.assertRedirects(response, encoded_url, fetch_redirect_response=False)
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, lang_code)
        with ignore_warnings(category=RemovedInDjango40Warning):
            self.assertEqual(self.client.session[LANGUAGE_SESSION_KEY], lang_code)

    @modify_settings(MIDDLEWARE={
        'append': 'django.middleware.locale.LocaleMiddleware',
    })
    def test_lang_from_translated_i18n_pattern(self):
        response = self.client.post(
            '/i18n/setlang/', data={'language': 'nl'},
            follow=True, HTTP_REFERER='/en/translated/'
        )
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, 'nl')
        with ignore_warnings(category=RemovedInDjango40Warning):
            self.assertEqual(self.client.session[LANGUAGE_SESSION_KEY], 'nl')
        self.assertRedirects(response, '/nl/vertaald/')
        # And reverse
        response = self.client.post(
            '/i18n/setlang/', data={'language': 'en'},
            follow=True, HTTP_REFERER='/nl/vertaald/'
        )
        self.assertRedirects(response, '/en/translated/')


@override_settings(ROOT_URLCONF='view_tests.urls')
class I18NViewTests(SimpleTestCase):
    """Test django.views.i18n views other than set_language."""
    @override_settings(LANGUAGE_CODE='de')
    def test_get_formats(self):
        formats = get_formats()
        # Test 3 possible types in get_formats: integer, string, and list.
        self.assertEqual(formats['FIRST_DAY_OF_WEEK'], 0)
        self.assertEqual(formats['DECIMAL_SEPARATOR'], '.')
        self.assertEqual(formats['TIME_INPUT_FORMATS'], ['%H:%M:%S', '%H:%M:%S.%f', '%H:%M'])

    def test_jsi18n(self):
        """The javascript_catalog can be deployed with language settings"""
        for lang_code in ['es', 'fr', 'ru']:
            with override(lang_code):
                catalog = gettext.translation('djangojs', locale_dir, [lang_code])
                trans_txt = catalog.gettext('this is to be translated')
                response = self.client.get('/jsi18n/')
                self.assertEqual(response['Content-Type'], 'text/javascript; charset="utf-8"')
                # response content must include a line like:
                # "this is to be translated": <value of trans_txt Python variable>
                # json.dumps() is used to be able to check unicode strings
                self.assertContains(response, json.dumps(trans_txt), 1)
                if lang_code == 'fr':
                    # Message with context (msgctxt)
                    self.assertContains(response, '"month name\\u0004May": "mai"', 1)

    @override_settings(USE_I18N=False)
    def test_jsi18n_USE_I18N_False(self):
        response = self.client.get('/jsi18n/')
        # default plural function
        self.assertContains(response, 'django.pluralidx = function(count) { return (count == 1) ? 0 : 1; };')
        self.assertNotContains(response, 'var newcatalog =')

    def test_jsoni18n(self):
        """
        The json_catalog returns the language catalog and settings as JSON.
        """
        with override('de'):
            response = self.client.get('/jsoni18n/')
            data = json.loads(response.content.decode())
            self.assertIn('catalog', data)
            self.assertIn('formats', data)
            self.assertEqual(data['formats']['TIME_INPUT_FORMATS'], ['%H:%M:%S', '%H:%M:%S.%f', '%H:%M'])
            self.assertEqual(data['formats']['FIRST_DAY_OF_WEEK'], 0)
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
            response = self.client.get('/jsi18n/')
            self.assertNotContains(response, 'esto tiene que ser traducido')

    def test_jsoni18n_with_missing_en_files(self):
        """
        Same as above for the json_catalog view. Here we also check for the
        expected JSON format.
        """
        with self.settings(LANGUAGE_CODE='es'), override('en-us'):
            response = self.client.get('/jsoni18n/')
            data = json.loads(response.content.decode())
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
            response = self.client.get('/jsi18n/')
            self.assertContains(response, 'il faut le traduire')
            self.assertNotContains(response, "Untranslated string")

    def test_i18n_fallback_language_plural(self):
        """
        The fallback to a language with less plural forms maintains the real
        language's number of plural forms and correct translations.
        """
        with self.settings(LANGUAGE_CODE='pt'), override('ru'):
            response = self.client.get('/jsi18n/')
            self.assertEqual(
                response.context['catalog']['{count} plural3'],
                ['{count} plural3 p3', '{count} plural3 p3s', '{count} plural3 p3t']
            )
            self.assertEqual(
                response.context['catalog']['{count} plural2'],
                ['{count} plural2', '{count} plural2s', '']
            )
        with self.settings(LANGUAGE_CODE='ru'), override('pt'):
            response = self.client.get('/jsi18n/')
            self.assertEqual(
                response.context['catalog']['{count} plural3'],
                ['{count} plural3', '{count} plural3s']
            )
            self.assertEqual(
                response.context['catalog']['{count} plural2'],
                ['{count} plural2', '{count} plural2s']
            )

    def test_i18n_english_variant(self):
        with override('en-gb'):
            response = self.client.get('/jsi18n/')
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
            self.assertContains(response, 'emoji')
            self.assertContains(response, '\\ud83d\\udca9')

    @modify_settings(INSTALLED_APPS={'append': ['view_tests.app1', 'view_tests.app2']})
    def test_i18n_language_english_default(self):
        """
        Check if the JavaScript i18n view returns a complete language catalog
        if the default language is en-us, the selected language has a
        translation available and a catalog composed by djangojs domain
        translations of multiple Python packages is requested. See #13388,
        #3594 and #13514 for more details.
        """
        base_trans_string = 'il faut traduire cette cha\\u00eene de caract\\u00e8res de '
        app1_trans_string = base_trans_string + 'app1'
        app2_trans_string = base_trans_string + 'app2'
        with self.settings(LANGUAGE_CODE='en-us'), override('fr'):
            response = self.client.get('/jsi18n_multi_packages1/')
            self.assertContains(response, app1_trans_string)
            self.assertContains(response, app2_trans_string)

            response = self.client.get('/jsi18n/app1/')
            self.assertContains(response, app1_trans_string)
            self.assertNotContains(response, app2_trans_string)

            response = self.client.get('/jsi18n/app2/')
            self.assertNotContains(response, app1_trans_string)
            self.assertContains(response, app2_trans_string)

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
        extended_locale_paths = settings.LOCALE_PATHS + [
            path.join(
                path.dirname(path.dirname(path.abspath(__file__))),
                'app3',
                'locale',
            ),
        ]
        with self.settings(LANGUAGE_CODE='es-ar', LOCALE_PATHS=extended_locale_paths):
            with override('es-ar'):
                response = self.client.get('/jsi18n/')
                self.assertContains(response, 'este texto de app3 debe ser traducido')

    def test_i18n_unknown_package_error(self):
        view = JavaScriptCatalog.as_view()
        request = RequestFactory().get('/')
        msg = 'Invalid package(s) provided to JavaScriptCatalog: unknown_package'
        with self.assertRaisesMessage(ValueError, msg):
            view(request, packages='unknown_package')
        msg += ',unknown_package2'
        with self.assertRaisesMessage(ValueError, msg):
            view(request, packages='unknown_package+unknown_package2')


@override_settings(ROOT_URLCONF='view_tests.urls')
class I18nSeleniumTests(SeleniumTestCase):

    # The test cases use fixtures & translations from these apps.
    available_apps = [
        'django.contrib.admin', 'django.contrib.auth',
        'django.contrib.contenttypes', 'view_tests',
    ]

    @override_settings(LANGUAGE_CODE='de')
    def test_javascript_gettext(self):
        self.selenium.get(self.live_server_url + '/jsi18n_template/')

        elem = self.selenium.find_element_by_id("gettext")
        self.assertEqual(elem.text, "Entfernen")
        elem = self.selenium.find_element_by_id("ngettext_sing")
        self.assertEqual(elem.text, "1 Element")
        elem = self.selenium.find_element_by_id("ngettext_plur")
        self.assertEqual(elem.text, "455 Elemente")
        elem = self.selenium.find_element_by_id("ngettext_onnonplural")
        self.assertEqual(elem.text, "Bild")
        elem = self.selenium.find_element_by_id("pgettext")
        self.assertEqual(elem.text, "Kann")
        elem = self.selenium.find_element_by_id("npgettext_sing")
        self.assertEqual(elem.text, "1 Resultat")
        elem = self.selenium.find_element_by_id("npgettext_plur")
        self.assertEqual(elem.text, "455 Resultate")
        elem = self.selenium.find_element_by_id("formats")
        self.assertEqual(
            elem.text,
            "DATE_INPUT_FORMATS is an object; DECIMAL_SEPARATOR is a string; FIRST_DAY_OF_WEEK is a number;"
        )

    @modify_settings(INSTALLED_APPS={'append': ['view_tests.app1', 'view_tests.app2']})
    @override_settings(LANGUAGE_CODE='fr')
    def test_multiple_catalogs(self):
        self.selenium.get(self.live_server_url + '/jsi18n_multi_catalogs/')

        elem = self.selenium.find_element_by_id('app1string')
        self.assertEqual(elem.text, 'il faut traduire cette chaîne de caractères de app1')
        elem = self.selenium.find_element_by_id('app2string')
        self.assertEqual(elem.text, 'il faut traduire cette chaîne de caractères de app2')
