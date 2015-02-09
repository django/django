import warnings

from django.apps import apps
from django.utils.deprecation import RemovedInDjango19Warning

warnings.warn(
    "The utilities in django.db.models.loading are deprecated "
    "in favor of the new application loading system.",
    RemovedInDjango19Warning, stacklevel=2)

__all__ = ('get_apps', 'get_app', 'get_models', 'get_model', 'register_models',
        'load_app', 'app_cache_ready')

# Backwards-compatibility for private APIs during the deprecation period.
UnavailableApp = LookupError
cache = apps

# These methods were always module level, so are kept that way for backwards
# compatibility.
get_apps = apps.get_apps
get_app_package = apps.get_app_package
get_app_path = apps.get_app_path
get_app_paths = apps.get_app_paths
get_app = apps.get_app
get_models = apps.get_models
get_model = apps.get_model
register_models = apps.register_models
load_app = apps.load_app
app_cache_ready = apps.app_cache_ready


# This method doesn't return anything interesting in Django 1.6. Maintain it
# just for backwards compatibility until this module is deprecated.
def get_app_errors():
    try:
        return apps.app_errors
    except AttributeError:
        apps.app_errors = {}
        return apps.app_errors
