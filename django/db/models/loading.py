import warnings

from django.apps import app_cache

warnings.warn(
    "The utilities in django.db.models.loading are deprecated "
    "in favor of the new application loading system.",
    PendingDeprecationWarning, stacklevel=2)

__all__ = ('get_apps', 'get_app', 'get_models', 'get_model', 'register_models',
        'load_app', 'app_cache_ready')

# These methods were always module level, so are kept that way for backwards
# compatibility.
get_apps = app_cache.get_apps
get_app_package = app_cache.get_app_package
get_app_path = app_cache.get_app_path
get_app_paths = app_cache.get_app_paths
get_app = app_cache.get_app
get_app_errors = app_cache.get_app_errors
get_models = app_cache.get_models
get_model = app_cache.get_model
register_models = app_cache.register_models
load_app = app_cache.load_app
app_cache_ready = app_cache.app_cache_ready
