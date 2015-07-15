from django.conf import settings
from django.core import checks
from django.test import SimpleTestCase


class SessionSettingsTests(SimpleTestCase):

    @property
    def func(self):
        from django.contrib.sessions.checks import check_names_conflict
        return check_names_conflict

    def test_language_session_and_csrf_cookies_names_defaults(self):
        cookie_values = (
            settings.CSRF_COOKIE_NAME,
            settings.LANGUAGE_COOKIE_NAME,
            settings.SESSION_COOKIE_NAME,
        )
        self.assertEqual(len(cookie_values), len(set(cookie_values)))
        self.assertEqual(self.func(), [])

    def test_csrf_language_and_session_cookie_names_are_all_different(self):
        cookies_settings = dict(
            CSRF_COOKIE_NAME='foo',
            LANGUAGE_COOKIE_NAME='bar',
            SESSION_COOKIE_NAME='foobar',
        )

        with self.settings(**cookies_settings):
            self.assertEqual(self.func(), [])

    def test_csrf_language_and_session_cookie_names_are_all_equal(self):
        cookie_settings = dict(
            CSRF_COOKIE_NAME='foo',
            LANGUAGE_COOKIE_NAME='foo',
            SESSION_COOKIE_NAME='foo',
        )
        expected = [
            checks.Error(
                "The 'LANGUAGE_COOKIE_NAME' and 'SESSION_COOKIE_NAME' settings must be different.",
                id='sessions.E001',
            ),
            checks.Error(
                "The 'CSRF_COOKIE_NAME' and 'LANGUAGE_COOKIE_NAME' settings must be different.",
                id='sessions.E001',
            ),
            checks.Error(
                "The 'CSRF_COOKIE_NAME' and 'SESSION_COOKIE_NAME' settings must be different.",
                id='sessions.E001',
            ),
        ]
        with self.settings(**cookie_settings):
            self.assertEqual(self.func(), expected)

    def test_csrf_and_language_cookie_names_are_equal(self):
        cookie_settings = dict(
            CSRF_COOKIE_NAME='foo',
            LANGUAGE_COOKIE_NAME='foo',
            SESSION_COOKIE_NAME='bar',
        )
        expected = [
            checks.Error(
                "The 'CSRF_COOKIE_NAME' and 'LANGUAGE_COOKIE_NAME' settings must be different.",
                id='sessions.E001',
            ),
        ]
        with self.settings(**cookie_settings):
            self.assertEqual(self.func(), expected)

    def test_csrf_and_session_cookie_names_are_equal(self):
        cookie_settings = dict(
            CSRF_COOKIE_NAME='foo',
            LANGUAGE_COOKIE_NAME='bar',
            SESSION_COOKIE_NAME='foo',
        )
        expected = [
            checks.Error(
                "The 'CSRF_COOKIE_NAME' and 'SESSION_COOKIE_NAME' settings must be different.",
                id='sessions.E001',
            ),
        ]
        with self.settings(**cookie_settings):
            self.assertEqual(self.func(), expected)

    def test_language_and_session_cookie_names_are_equal(self):
        cookie_settings = dict(
            CSRF_COOKIE_NAME='bar',
            LANGUAGE_COOKIE_NAME='foo',
            SESSION_COOKIE_NAME='foo',
        )
        expected = [
            checks.Error(
                "The 'LANGUAGE_COOKIE_NAME' and 'SESSION_COOKIE_NAME' settings must be different.",
                id='sessions.E001',
            ),
        ]
        with self.settings(**cookie_settings):
            self.assertEqual(self.func(), expected)
