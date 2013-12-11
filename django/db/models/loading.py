import warnings

from django.apps.cache import cache

warnings.warn(
    "The utilities in django.db.models.loading are deprecated "
    "in favor of the new application loading system.",
    PendingDeprecationWarning, stacklevel=2)

__all__ = ('get_apps', 'get_app', 'get_models', 'get_model', 'register_models',
        'load_app', 'app_cache_ready')

# These methods were always module level, so are kept that way for backwards
# compatibility.
get_apps = cache.get_apps
get_app_package = cache.get_app_package
get_app_path = cache.get_app_path
get_app_paths = cache.get_app_paths
get_app = cache.get_app
get_app_errors = cache.get_app_errors
get_models = cache.get_models
get_model = cache.get_model
register_models = cache.register_models
load_app = cache.load_app
app_cache_ready = cache.app_cache_ready
