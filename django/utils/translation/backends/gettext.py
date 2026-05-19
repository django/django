"""
Gettext translation backend.

This is the default backend selected by :setting:`TRANSLATION_BACKEND`. It is a
thin object wrapper around the function-level API in
:mod:`django.utils.translation.trans_real`, which remains the implementation of
record so the existing gettext semantics and the entire ``tests/i18n`` suite
are preserved byte-for-byte.
"""

from django.utils.translation import trans_real
from django.utils.translation.backends import BaseTranslationBackend


class GettextBackend(BaseTranslationBackend):
    """
    Default backend. Delegates to :mod:`django.utils.translation.trans_real`.
    """

    # -- Translation surface --------------------------------------------

    def gettext(self, message):
        return trans_real.gettext(message)

    def ngettext(self, singular, plural, number):
        return trans_real.ngettext(singular, plural, number)

    def pgettext(self, context, message):
        return trans_real.pgettext(context, message)

    def npgettext(self, context, singular, plural, number):
        return trans_real.npgettext(context, singular, plural, number)

    def gettext_noop(self, message):
        return trans_real.gettext_noop(message)

    # -- Language state -------------------------------------------------

    def activate(self, language):
        return trans_real.activate(language)

    def deactivate(self):
        return trans_real.deactivate()

    def deactivate_all(self):
        return trans_real.deactivate_all()

    def get_language(self):
        return trans_real.get_language()

    def get_language_bidi(self):
        return trans_real.get_language_bidi()

    def get_language_from_request(self, request, check_path=False):
        return trans_real.get_language_from_request(request, check_path)

    def get_language_from_path(self, path):
        return trans_real.get_language_from_path(path)

    def get_supported_language_variant(self, lang_code, strict=False):
        return trans_real.get_supported_language_variant(lang_code, strict)

    def check_for_language(self, lang_code):
        return trans_real.check_for_language(lang_code)

    # -- Optional hooks -------------------------------------------------

    def clear_translations_cache(self):
        trans_real._translations = {}
        trans_real.check_for_language.cache_clear()

    def clear_active_language(self):
        from asgiref.local import Local

        trans_real._default = None
        trans_real._active = Local()

    def on_translation_files_changed(self, sender, file_path, **kwargs):
        # Also clear the stdlib gettext module's own cache: trans_real reuses
        # gettext.translation() which memoizes loaded .mo files there.
        import gettext as _gettext_module

        _gettext_module._translations = {}
        self.reset_state()

    def get_catalog(self, locale, domain="djangojs", localedirs=None):
        return trans_real.DjangoTranslation(
            locale, domain=domain, localedirs=localedirs
        )

    def is_valid_language_code(self, code):
        return bool(trans_real.language_code_re.match(code))
