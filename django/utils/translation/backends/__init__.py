"""
Translation backends.

A translation backend is a class that implements the surface defined by
:class:`BaseTranslationBackend` and powers the public ``gettext``,
``gettext_lazy``, ``activate``, ``get_language``… helpers exposed by
``django.utils.translation``.

The active backend is selected by the :setting:`TRANSLATION_BACKEND` setting.
When :setting:`USE_I18N` is ``False``, the null backend is forced regardless of
that setting.
"""

from django.utils.module_loading import import_string


class InvalidTranslationBackendError(ImportError):
    """Raised when TRANSLATION_BACKEND cannot be imported or instantiated."""


def load_backend(dotted_path):
    """
    Import and instantiate the backend at ``dotted_path``.

    Raised errors are wrapped in :class:`InvalidTranslationBackendError` so the
    dispatcher can surface a single, predictable exception type.
    """
    try:
        cls = import_string(dotted_path)
    except ImportError as exc:
        raise InvalidTranslationBackendError(
            "Could not import translation backend %r: %s" % (dotted_path, exc)
        ) from exc
    try:
        return cls()
    except TypeError as exc:
        raise InvalidTranslationBackendError(
            "Could not instantiate translation backend %r: %s" % (dotted_path, exc)
        ) from exc


class BaseTranslationBackend:
    """
    Base class third-party translation backends must subclass.

    The base implementation supplies sensible defaults for the optional hooks
    (``gettext_noop``, ``reset_state``, ``on_translation_files_changed``,
    ``get_catalog``, ``is_valid_language_code``). The mandatory methods raise
    :class:`NotImplementedError`; subclasses must override them.
    """

    # -- Mandatory translation surface ----------------------------------

    def gettext(self, message):
        raise NotImplementedError

    def ngettext(self, singular, plural, number):
        raise NotImplementedError

    def pgettext(self, context, message):
        raise NotImplementedError

    def npgettext(self, context, singular, plural, number):
        raise NotImplementedError

    # -- Mandatory language state surface -------------------------------

    def activate(self, language):
        raise NotImplementedError

    def deactivate(self):
        raise NotImplementedError

    def deactivate_all(self):
        raise NotImplementedError

    def get_language(self):
        raise NotImplementedError

    def get_language_bidi(self):
        raise NotImplementedError

    def get_language_from_request(self, request, check_path=False):
        raise NotImplementedError

    def get_language_from_path(self, path):
        raise NotImplementedError

    def get_supported_language_variant(self, lang_code, strict=False):
        raise NotImplementedError

    def check_for_language(self, lang_code):
        raise NotImplementedError

    # -- Optional hooks with usable defaults ----------------------------

    def gettext_noop(self, message):
        return message

    def clear_translations_cache(self):
        """
        Drop the cache of loaded translation catalogs without touching the
        per-thread active language. Triggered on INSTALLED_APPS changes.
        """

    def clear_active_language(self):
        """
        Forget the current default language and the per-thread active
        language. Triggered on LANGUAGES/LANGUAGE_CODE/LOCALE_PATHS changes.
        """

    def reset_state(self):
        """
        Drop every per-process cache the backend keeps.

        Called by ``django.test.signals`` between tests and by the autoreload
        translation watcher when a translation file changes on disk. The
        default composes the two finer-grained hooks above.
        """
        self.clear_translations_cache()
        self.clear_active_language()

    def on_translation_files_changed(self, sender, file_path, **kwargs):
        """
        React to a translation source file having changed on disk.

        The default implementation calls :meth:`reset_state`; backends that do
        not load from disk can leave this as a no-op by overriding to ``pass``.
        """
        self.reset_state()

    def get_catalog(self, locale, domain="djangojs", localedirs=None):
        """
        Return a translation catalog object for the
        :class:`~django.views.i18n.JavaScriptCatalog` view.

        The returned object must expose ``_catalog`` (``{msgid: msgstr}``)
        and ``_fallback`` (another catalog or ``None``). Backends that do
        not ship a JavaScript catalog should leave this raising
        :class:`NotImplementedError` — the view will surface a clear error.
        """
        raise NotImplementedError(
            "%s does not expose a JavaScript catalog." % type(self).__name__
        )

    def is_valid_language_code(self, code):
        """Return whether ``code`` is a syntactically valid language tag."""
        return True
