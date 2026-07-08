from datetime import timedelta

from django.core import signing
from django.http import HttpRequest, HttpResponse
from django.test import SimpleTestCase, override_settings
from django.test.utils import freeze_time, ignore_warnings
from django.utils.deprecation import RemovedInDjango70Warning


class SignedCookieTest(SimpleTestCase):
    def test_can_set_and_read_signed_cookies(self):
        response = HttpResponse()
        response.set_signed_cookie("c", "hello")
        self.assertIn("c", response.cookies)
        self.assertTrue(response.cookies["c"].value.startswith("hello:"))
        request = HttpRequest()
        request.COOKIES["c"] = response.cookies["c"].value
        value = request.get_signed_cookie("c")
        self.assertEqual(value, "hello")

    def test_can_use_salt(self):
        response = HttpResponse()
        response.set_signed_cookie("a", "hello", salt="one")
        request = HttpRequest()
        request.COOKIES["a"] = response.cookies["a"].value
        value = request.get_signed_cookie("a", salt="one")
        self.assertEqual(value, "hello")
        with self.assertRaises(signing.BadSignature):
            request.get_signed_cookie("a", salt="two")

    def test_salt_namespace_is_unambiguous(self):
        response = HttpResponse()
        response.set_signed_cookie("a", "hello", salt="bc")
        request = HttpRequest()
        request.COOKIES["ab"] = response.cookies["a"].value
        with self.assertRaises(signing.BadSignature):
            request.get_signed_cookie("ab", salt="c")

    # RemovedInDjango70Warning: When the deprecation ends, remove this test.
    @ignore_warnings(category=RemovedInDjango70Warning)
    @override_settings(SIGNED_COOKIE_LEGACY_SALT_FALLBACK=True)
    def test_expired_legacy_cookie_raises_signature_expired(self):
        with freeze_time(123456789):
            request = HttpRequest()
            request.COOKIES["a"] = signing.get_cookie_signer(
                salt=signing._cookie_signer_legacy_salt("a", "bc")
            ).sign("hello")
        with freeze_time(123456800):
            with self.assertRaises(signing.SignatureExpired):
                request.get_signed_cookie("a", salt="bc", max_age=10)

    # RemovedInDjango70Warning: When the deprecation ends, remove this test.
    @ignore_warnings(category=RemovedInDjango70Warning)
    @override_settings(SIGNED_COOKIE_LEGACY_SALT_FALLBACK=True)
    def test_legacy_salt_namespace_is_accepted(self):
        request = HttpRequest()
        # Simulate an attack along the lines of CVE-2026-6873, where a value
        # for the "a" cookie is submitted as the value for another cookie.
        request.COOKIES["ab"] = signing.get_cookie_signer(
            salt=signing._cookie_signer_legacy_salt("a", "bc")
        ).sign("hello")
        # No protection since SIGNED_COOKIE_LEGACY_SALT_FALLBACK=True.
        self.assertEqual(request.get_signed_cookie("ab", salt="c"), "hello")

    # RemovedInDjango70Warning: When the deprecation ends, remove this test.
    def test_legacy_salt_namespace_not_accepted(self):
        request = HttpRequest()
        request.COOKIES["a"] = signing.get_cookie_signer(
            salt=signing._cookie_signer_legacy_salt("a", "bc")
        ).sign("hello")
        with self.assertRaises(signing.BadSignature):
            request.get_signed_cookie("a", salt="bc")

    # RemovedInDjango70Warning: When the deprecation ends, remove this test.
    @ignore_warnings(category=RemovedInDjango70Warning)
    @override_settings(SIGNED_COOKIE_LEGACY_SALT_FALLBACK=True)
    def test_expired_new_style_cookie_does_not_fallback_to_legacy_salt(self):
        with freeze_time(123456789):
            response = HttpResponse()
            response.set_signed_cookie("a", "hello", salt="bc")
        request = HttpRequest()
        request.COOKIES["a"] = response.cookies["a"].value
        with freeze_time(123456800):
            with self.assertRaises(signing.SignatureExpired):
                request.get_signed_cookie("a", salt="bc", max_age=10)

    def test_detects_tampering(self):
        response = HttpResponse()
        response.set_signed_cookie("c", "hello")
        request = HttpRequest()
        request.COOKIES["c"] = response.cookies["c"].value[:-2] + "$$"
        with self.assertRaises(signing.BadSignature):
            request.get_signed_cookie("c")

    def test_default_argument_suppresses_exceptions(self):
        response = HttpResponse()
        response.set_signed_cookie("c", "hello")
        request = HttpRequest()
        request.COOKIES["c"] = response.cookies["c"].value[:-2] + "$$"
        self.assertIsNone(request.get_signed_cookie("c", default=None))

    def test_max_age_argument(self):
        value = "hello"
        with freeze_time(123456789):
            response = HttpResponse()
            response.set_signed_cookie("c", value)
            request = HttpRequest()
            request.COOKIES["c"] = response.cookies["c"].value
            self.assertEqual(request.get_signed_cookie("c"), value)

        with freeze_time(123456800):
            self.assertEqual(request.get_signed_cookie("c", max_age=12), value)
            self.assertEqual(request.get_signed_cookie("c", max_age=11), value)
            self.assertEqual(
                request.get_signed_cookie("c", max_age=timedelta(seconds=11)), value
            )
            with self.assertRaises(signing.SignatureExpired):
                request.get_signed_cookie("c", max_age=10)
            with self.assertRaises(signing.SignatureExpired):
                request.get_signed_cookie("c", max_age=timedelta(seconds=10))

    def test_set_signed_cookie_max_age_argument(self):
        response = HttpResponse()
        response.set_signed_cookie("c", "value", max_age=100)
        self.assertEqual(response.cookies["c"]["max-age"], 100)
        response.set_signed_cookie("d", "value", max_age=timedelta(hours=2))
        self.assertEqual(response.cookies["d"]["max-age"], 7200)

    @override_settings(SECRET_KEY=b"\xe7")
    def test_signed_cookies_with_binary_key(self):
        response = HttpResponse()
        response.set_signed_cookie("c", "hello")

        request = HttpRequest()
        request.COOKIES["c"] = response.cookies["c"].value
        self.assertEqual(request.get_signed_cookie("c"), "hello")
