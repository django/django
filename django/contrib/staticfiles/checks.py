from django.conf import STATICFILES_STORAGE_ALIAS, settings
from django.contrib.staticfiles.finders import get_finders
from django.core.checks import Error

E005 = Error(
    f"The STORAGES setting must define a '{STATICFILES_STORAGE_ALIAS}' storage.",
    id="staticfiles.E005",
)


def check_finders(app_configs, **kwargs):
    """Check all registered staticfiles finders."""
    errors = []
    for finder in get_finders():
        try:
            finder_errors = finder.check()
        except NotImplementedError:
            pass
        else:
            errors.extend(finder_errors)
    return errors


def check_storages(app_configs, **kwargs):
    """Ensure staticfiles is defined in STORAGES setting."""
    errors = []
    if STATICFILES_STORAGE_ALIAS not in settings.STORAGES:
        errors.append(E005)
    return errors
