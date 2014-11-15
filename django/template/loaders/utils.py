import warnings

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import lru_cache
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.module_loading import import_string


@lru_cache.lru_cache()
def get_template_loaders():
    loaders = []
    for loader_name in settings.TEMPLATE_LOADERS:
        loader = find_template_loader(loader_name)
        if loader is not None:
            loaders.append(loader)
    # Immutable return value because it will be cached and shared by callers.
    return tuple(loaders)


def find_template_loader(loader):
    if isinstance(loader, (tuple, list)):
        loader, args = loader[0], loader[1:]
    else:
        args = []
    if isinstance(loader, six.string_types):
        TemplateLoader = import_string(loader)

        if hasattr(TemplateLoader, 'load_template_source'):
            func = TemplateLoader(*args)
        else:
            warnings.warn(
                "Function-based template loaders are deprecated. "
                "Please use class-based template loaders instead. "
                "Inherit django.template.loaders.base.Loader "
                "and provide a load_template_source() method.",
                RemovedInDjango20Warning, stacklevel=2)

            # Try loading module the old way - string is full path to callable
            if args:
                raise ImproperlyConfigured(
                    "Error importing template source loader %s - can't pass "
                    "arguments to function-based loader." % loader)
            func = TemplateLoader

        if not func.is_usable:
            warnings.warn(
                "Your TEMPLATE_LOADERS setting includes %r, but your Python "
                "installation doesn't support that type of template loading. "
                "Consider removing that line from TEMPLATE_LOADERS." % loader)
            return None
        else:
            return func
    else:
        raise ImproperlyConfigured(
            "Invalid value in TEMPLATE_LOADERS: %r" % loader)
