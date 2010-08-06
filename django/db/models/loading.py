"Utilities for loading models and the modules that contain them."

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.datastructures import SortedDict
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule
from django.core.apps import App

import imp
import sys
import os
import threading

__all__ = ('get_apps', 'get_app', 'get_models', 'get_model', 'register_models',
        'load_app', 'app_cache_ready')

from django.core.apps import AppCache
cache = AppCache()

# These methods were always module level, so are kept that way for backwards
# compatibility.
get_apps = cache.get_apps
get_app = cache.get_app
get_app_errors = cache.get_app_errors
get_models = cache.get_models
get_model = cache.get_model
register_models = cache.register_models
load_app = cache.load_app
app_cache_ready = cache.app_cache_ready
