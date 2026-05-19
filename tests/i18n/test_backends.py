"""
Tests for the pluggable translation backend extension point introduced by the
``TRANSLATION_BACKEND`` setting (ticket #14974).

These tests assert dispatcher behavior; the existing ``tests/i18n`` suite is
the oracle that gettext semantics remain untouched.
"""

from django.core.checks import Error
from django.test import SimpleTestCase, override_settings
from django.utils.translation import (
    _trans,
    gettext,
    gettext_lazy,
    ngettext,
    pgettext,
)
from django.utils.translation.backends import (
    BaseTranslationBackend,
    InvalidTranslationBackendError,
    load_backend,
)


def _reset_dispatcher():
    """
    Drop attributes cached on the ``_trans`` dispatcher so the next call goes
    through ``__getattr__`` and re-reads ``settings.TRANSLATION_BACKEND``.
    """
    for name in list(_trans.__dict__):
        delattr(_trans, name)


class StubBackend(BaseTranslationBackend):
    """Backend that wraps every message — easy to detect in assertions."""

    def gettext(self, message):
        return "<<%s>>" % message

    def ngettext(self, singular, plural, number):
        return self.gettext(singular if number == 1 else plural)

    def pgettext(self, context, message):
        return "<<%s|%s>>" % (context, message)

    def npgettext(self, context, singular, plural, number):
        return self.pgettext(context, singular if number == 1 else plural)

    def activate(self, language):
        self._language = language

    def deactivate(self):
        self._language = None

    def deactivate_all(self):
        self._language = None

    def get_language(self):
        return getattr(self, "_language", "en")

    def get_language_bidi(self):
        return False

    def get_language_from_request(self, request, check_path=False):
        return "en"

    def get_language_from_path(self, path):
        return None

    def get_supported_language_variant(self, lang_code, strict=False):
        return lang_code

    def check_for_language(self, lang_code):
        return True

    def is_valid_language_code(self, code):
        # Stub backend accepts everything that's a non-empty string.
        return isinstance(code, str) and bool(code)


STUB_BACKEND = "i18n.test_backends.StubBackend"


class LoadBackendTests(SimpleTestCase):
    def test_load_backend_returns_instance(self):
        self.assertIsInstance(load_backend(STUB_BACKEND), StubBackend)

    def test_load_backend_invalid_path(self):
        with self.assertRaises(InvalidTranslationBackendError):
            load_backend("does.not.exist.Backend")

    def test_load_backend_invalid_class(self):
        # A class whose __init__ refuses no-arg construction surfaces as
        # InvalidTranslationBackendError, not a bare TypeError.
        with self.assertRaises(InvalidTranslationBackendError):
            load_backend("i18n.test_backends.BackendThatRequiresArgs")


class BackendThatRequiresArgs(BaseTranslationBackend):
    def __init__(self, required_arg):
        self.required_arg = required_arg


class BaseBackendDefaultsTests(SimpleTestCase):
    def test_gettext_noop_default_is_identity(self):
        backend = BaseTranslationBackend()
        self.assertEqual(backend.gettext_noop("Hello"), "Hello")

    def test_reset_state_calls_both_clear_hooks(self):
        seen = []

        class TrackingBackend(BaseTranslationBackend):
            def clear_translations_cache(self):
                seen.append("translations")

            def clear_active_language(self):
                seen.append("language")

        TrackingBackend().reset_state()
        self.assertEqual(seen, ["translations", "language"])

    def test_get_catalog_default_raises(self):
        with self.assertRaisesMessage(
            NotImplementedError, "does not expose a JavaScript catalog"
        ):
            BaseTranslationBackend().get_catalog("en")

    def test_is_valid_language_code_default_permissive(self):
        self.assertTrue(BaseTranslationBackend().is_valid_language_code("anything"))


class DispatcherSelectionTests(SimpleTestCase):
    def setUp(self):
        _reset_dispatcher()
        self.addCleanup(_reset_dispatcher)

    @override_settings(TRANSLATION_BACKEND=STUB_BACKEND)
    def test_gettext_routes_through_active_backend(self):
        self.assertEqual(gettext("Hello"), "<<Hello>>")

    @override_settings(TRANSLATION_BACKEND=STUB_BACKEND)
    def test_ngettext_routes_through_active_backend(self):
        self.assertEqual(ngettext("apple", "apples", 1), "<<apple>>")
        self.assertEqual(ngettext("apple", "apples", 2), "<<apples>>")

    @override_settings(TRANSLATION_BACKEND=STUB_BACKEND)
    def test_pgettext_routes_through_active_backend(self):
        self.assertEqual(pgettext("month", "May"), "<<month|May>>")

    @override_settings(TRANSLATION_BACKEND=STUB_BACKEND)
    def test_lazy_resolves_against_active_backend(self):
        # gettext_lazy is built once at import time but the proxy must resolve
        # against the *current* dispatcher state on each str() call.
        self.assertEqual(str(gettext_lazy("Hello")), "<<Hello>>")

    @override_settings(USE_I18N=False, TRANSLATION_BACKEND=STUB_BACKEND)
    def test_use_i18n_false_overrides_backend_setting(self):
        # NullBackend must win regardless of TRANSLATION_BACKEND.
        self.assertEqual(gettext("Hello"), "Hello")

    @override_settings(TRANSLATION_BACKEND="x.y.z.NotARealClass")
    def test_invalid_backend_surfaces_clear_error(self):
        with self.assertRaises(InvalidTranslationBackendError):
            gettext("Hello")


class SystemCheckIntegrationTests(SimpleTestCase):
    """The translation system checks must route through the backend."""

    def setUp(self):
        _reset_dispatcher()
        self.addCleanup(_reset_dispatcher)

    @override_settings(
        TRANSLATION_BACKEND=STUB_BACKEND,
        LANGUAGE_CODE="anything-goes-with-stub",
        LANGUAGES=[("anything-goes-with-stub", "Anything")],
    )
    def test_language_code_check_defers_to_backend(self):
        # The stub backend accepts arbitrary non-empty strings as language
        # codes. The gettext backend would reject "anything-goes-with-stub".
        from django.core.checks.translation import (
            check_setting_language_code,
            check_setting_languages,
        )

        self.assertEqual(check_setting_language_code(None), [])
        self.assertEqual(check_setting_languages(None), [])

    @override_settings(TRANSLATION_BACKEND=STUB_BACKEND, LANGUAGE_CODE="")
    def test_language_code_check_rejects_empty_under_stub(self):
        from django.core.checks.translation import check_setting_language_code

        errors = check_setting_language_code(None)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], Error)
        self.assertEqual(errors[0].id, "translation.E001")
