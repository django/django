from django.conf import settings
_installed_models_cache = None

def get_installed_models():
    """
    Returns a list of installed "models" packages, such as foo.models,
    ellington.news.models, etc. This does NOT include django.models.
    """
    global _installed_models_cache
    if _installed_models_cache is not None:
        return _installed_models_cache
    _installed_models_cache = []
    for a in settings.INSTALLED_APPS:
        try:
            _installed_models_cache.append(__import__(a + '.models', '', '', ['']))
        except ImportError, e:
            pass
    return _installed_models_cache

_installed_modules_cache = None

def add_model_module(mod, modules):
    if hasattr(mod, '_MODELS'):
        modules.append(mod)
    for name in getattr(mod, '__all__', []):
        submod = __import__("%s.%s" % (mod.__name__, name), '', '', [''])
        add_model_module(submod, modules)

def get_installed_model_modules():
    """
    Returns a list of installed models, such as django.models.core,
    ellington.news.models.news, foo.models.bar, etc.
    """
    global _installed_modules_cache
    if _installed_modules_cache is not None:
        return _installed_modules_cache
    _installed_modules_cache = []
    for mod in get_installed_models():
        add_model_module(mod, _installed_modules_cache)
    return _installed_modules_cache
