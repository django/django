from django.core.exceptions import ImproperlyConfigured
from django.utils.version import get_version

VERSION = (3, 0, 0, 'alpha', 0)

__version__ = get_version(VERSION)


# Flag also used to prevent multiple setup() calls
is_ready = False


def _setup(set_prefix=True):
    """
    Configure the settings (this happens as a side effect of accessing the
    first setting), configure logging and populate the app registry.
    Set the thread-local urlresolvers script prefix if `set_prefix` is True.
    """
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


def setup(set_prefix=True):
    """
    This function is idempotent (calling it several times changes nothing), but
    not reentrant (recursively calling it would have an unexpected result).

    It delegates actual setup of Django to settings.DJANGO_SETUP_CALLABLE  (if set),
    else to ``django._setup``

    Returns True iff actual setup occurred.
    """
    global is_ready
    if is_ready:
        return False

    from django.conf import settings
    from importlib import import_module

    if settings.DJANGO_SETUP_CALLABLE:
        try:
            mod_path, _, callable_name = settings.DJANGO_SETUP_CALLABLE.rpartition('.')
            mod = import_module(mod_path)
            setup_callable = getattr(mod, callable_name)
            setup_callable()  # No arguments expected for this callable
        except (ImportError, AttributeError) as exc:
            raise ImproperlyConfigured("Could not load '%s' callable (%r)." %
                                       (settings.DJANGO_SETUP_CALLABLE, exc))
    else:
        # Default case: do standard apps/logging setup
        _setup(set_prefix=set_prefix)

    # Only now that setup was successful, we prevent later recalls
    is_ready = True
    return True
