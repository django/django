import threading

from django.utils.version import get_version

VERSION = (3, 0, 0, 'alpha', 0)

__version__ = get_version(VERSION)


# Flag also used to prevent multiple setup() calls
is_ready = False
_is_loading = False

_setup_lock = threading.RLock()


def setup(set_prefix=True):
    """
    Configure the settings (this happens as a side effect of accessing the
    first setting), configure logging and populate the app registry.
    Set the thread-local urlresolvers script prefix if `set_prefix` is True.

    This function is thread-safe and idempotent (calling it several times changes nothing), but
    not reentrant (recursively calling it results in a deadlock).

    Returns a boolean indicating whether setup occurred for the first time."
    """

    global is_ready, _is_loading

    # setup() might be called by multiple threads in parallel, on servers that create threads
    # before initializing the WSGI callable.
    # This RLock prevents other threads from entering this section. The "compare and set" operation
    # it performs is atomic.
    with _setup_lock:

        if is_ready:
            return False

        if _is_loading:
            # Prevent reentrant calls to avoid running initialization twice.
            raise RuntimeError("django.setup() isn't reentrant")

        try:
            _is_loading = True

            from django.apps import apps
            from django.conf import settings
            from django.urls import set_script_prefix
            from django.utils.log import configure_logging
            configure_logging(settings.LOGGING_CONFIG, settings.LOGGING)
            if set_prefix:
                set_script_prefix(
                    '/' if settings.FORCE_SCRIPT_NAME is None else settings.FORCE_SCRIPT_NAME
                )
            apps.populate(settings.INSTALLED_APPS)
        finally:
            # Cleanup in case initialization failed
            _is_loading = False

        is_ready = True
        return True
