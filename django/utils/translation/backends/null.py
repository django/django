"""
Null translation backend.

Used when :setting:`USE_I18N` is ``False`` (or when a project sets
``TRANSLATION_BACKEND`` to this class explicitly). It returns messages
unchanged, mirroring the behavior of
:mod:`django.utils.translation.trans_null`, which remains the implementation
of record.
"""

from django.utils.translation import trans_null
from django.utils.translation.backends import BaseTranslationBackend


class NullBackend(BaseTranslationBackend):
    """No-op backend; delegates to ``django.utils.translation.trans_null``."""

    def gettext(self, message):
        return trans_null.gettext(message)

    def ngettext(self, singular, plural, number):
        return trans_null.ngettext(singular, plural, number)

    def pgettext(self, context, message):
        return trans_null.pgettext(context, message)

    def npgettext(self, context, singular, plural, number):
        return trans_null.npgettext(context, singular, plural, number)

    def gettext_noop(self, message):
        return trans_null.gettext_noop(message)

    def activate(self, language):
        return trans_null.activate(language)

    def deactivate(self):
        return trans_null.deactivate()

    def deactivate_all(self):
        return trans_null.deactivate_all()

    def get_language(self):
        return trans_null.get_language()

    def get_language_bidi(self):
        return trans_null.get_language_bidi()

    def get_language_from_request(self, request, check_path=False):
        return trans_null.get_language_from_request(request, check_path)

    def get_language_from_path(self, path):
        return trans_null.get_language_from_path(path)

    def get_supported_language_variant(self, lang_code, strict=False):
        return trans_null.get_supported_language_variant(lang_code, strict)

    def check_for_language(self, lang_code):
        return trans_null.check_for_language(lang_code)
