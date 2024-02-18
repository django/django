"""Module contains tests related to Django settings."""

import time
from collections import namedtuple

from django.core.checks.settings import check_settings_types
from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.utils.functional import SimpleLazyObject, lazy


class SettingsCheckTests(SimpleTestCase):
    def _assertCheck(self, **settings):
        with override_settings(**settings):
            return check_settings_types(None)

    def _assertCheckFail(self, type_msg, **settings):
        errors_and_warnings = self._assertCheck(**settings)
        self.assertEqual(len(errors_and_warnings), 1, errors_and_warnings)
        self.assertEqual(errors_and_warnings[0].id, "settings.W001")
        self.assertEqual(
            f"The type of the {next(iter(settings))} setting should be {type_msg}.",
            errors_and_warnings[0].msg,
        )

    def _assertCheckPass(self, **settings):
        errors_and_warnings = self._assertCheck(**settings)
        self.assertEqual(len(errors_and_warnings), 0)

    def test_setting_boolean(self):
        self._assertCheckPass(DEBUG=True)
        for value in [None, object(), 0, 0.0, [], ("tuple",), "True"]:
            with self.subTest(value=value):
                self._assertCheckFail("bool", DEBUG=value)

    def test_setting_string(self):
        self._assertCheckPass(DEFAULT_FROM_EMAIL="a@b.de")
        for value in [None, object(), True, 1, 1.0, ["a@b.de"], ("tuple",)]:
            with self.subTest(value=value):
                self._assertCheckFail("str", DEFAULT_FROM_EMAIL=value)

    def test_setting_list(self):
        self._assertCheckPass(LANGUAGES_BIDI=["ar-dz"])
        for value in [None, object(), True, 1, 1.0, ("tuple",), "ar-dz"]:
            with self.subTest(value=value):
                self._assertCheckFail("list", LANGUAGES_BIDI=value)

    def test_setting_tuple_or_None(self):
        self._assertCheckPass(SECURE_PROXY_SSL_HEADER=("HEADER", "VALUE"))
        self._assertCheckPass(SECURE_PROXY_SSL_HEADER=None)
        for value in [object(), True, 1, 1.0, ["HEADER", "VALUE"], "ar-dz"]:
            with self.subTest(value=value):
                self._assertCheckFail("tuple or None", SECURE_PROXY_SSL_HEADER=value)

    def test_setting_tuple_subclass(self):
        CustomHeader = namedtuple("CustomHeader", "header value")
        custom_header = CustomHeader("HEADER", "VALUE")
        self._assertCheckPass(SECURE_PROXY_SSL_HEADER=custom_header)

    def test_setting_string_or_boolean(self):
        self._assertCheckPass(SESSION_COOKIE_SAMESITE="Lax")
        self._assertCheckPass(SESSION_COOKIE_SAMESITE=True)
        for value in [None, object(), 1, 1.0, ("Strict",), ["Strict"]]:
            with self.subTest(value=value):
                self._assertCheckFail("str or bool", SESSION_COOKIE_SAMESITE=value)

    def test_setting_custom(self):
        for value in [None, object(), 1**6, 1e6, ("crunchy",), ["brownies"]]:
            with self.subTest(value=value):
                self._assertCheckPass(COOKIE_MONSTER_FAVORITES=value)

    def test_setting_lazy(self):
        weeks = lazy(lambda w: 60 * 60 * 24 * 7 * w, int)
        self._assertCheckPass(SESSION_COOKIE_AGE=weeks(2))

    def test_setting_lazy_object(self):
        def get_time():
            return int(time.time())

        self._assertCheckPass(CACHE_MIDDLEWARE_SECONDS=SimpleLazyObject(get_time))
