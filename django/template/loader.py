import warnings

from django.conf import settings
from django.utils.deprecation import RemovedInDjango20Warning

from .base import Origin
from .engine import Engine


class LoaderOrigin(Origin):
    def __init__(self, display_name, loader, name, dirs):
        super(LoaderOrigin, self).__init__(display_name)
        self.loader, self.loadname, self.dirs = loader, name, dirs

    def reload(self):
        return self.loader(self.loadname, self.dirs)[0]


def make_origin(display_name, loader, name, dirs):
    if settings.TEMPLATE_DEBUG and display_name:
        return LoaderOrigin(display_name, loader, name, dirs)
    else:
        return None


def find_template(*args, **kwargs):
    return Engine.get_default().find_template(*args, **kwargs)


def get_template(*args, **kwargs):
    return Engine.get_default().get_template(*args, **kwargs)


def get_template_from_string(*args, **kwargs):
    return Engine.get_default().get_template_from_string(*args, **kwargs)


def render_to_string(*args, **kwargs):
    return Engine.get_default().render_to_string(*args, **kwargs)


def select_template(*args, **kwargs):
    return Engine.get_default().select_template(*args, **kwargs)


# This line must remain at the bottom to avoid import loops.
from .loaders import base


class BaseLoader(base.Loader):
    _accepts_engine_in_init = False

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "django.template.loader.BaseLoader was superseded by "
            "django.template.loaders.base.Loader.",
            RemovedInDjango20Warning, stacklevel=2)
        super(BaseLoader, self).__init__(*args, **kwargs)
