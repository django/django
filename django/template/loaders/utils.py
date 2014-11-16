import warnings

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import lru_cache
from django.utils import six
from django.utils.module_loading import import_string


@lru_cache.lru_cache()
def get_template_loaders():
    return _get_template_loaders(settings.TEMPLATE_LOADERS)


def _get_template_loaders(template_loaders=None):
    loaders = []
    for template_loader in template_loaders:
        loader = find_template_loader(template_loader)
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
        loader_class = import_string(loader)
        loader_instance = loader_class(*args)

        if not loader_instance.is_usable:
            warnings.warn(
                "Your TEMPLATE_LOADERS setting includes %r, but your Python "
                "installation doesn't support that type of template loading. "
                "Consider removing that line from TEMPLATE_LOADERS." % loader)
            return None
        else:
            return loader_instance

    else:
        raise ImproperlyConfigured(
            "Invalid value in TEMPLATE_LOADERS: %r" % loader)
