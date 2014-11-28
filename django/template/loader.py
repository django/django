import warnings

from django.utils.deprecation import RemovedInDjango20Warning

from . import engines
from .backends.django import DjangoTemplates
from .base import Origin, TemplateDoesNotExist
from .engine import _dirs_undefined, Engine


class LoaderOrigin(Origin):
    def __init__(self, display_name, loader, name, dirs):
        super(LoaderOrigin, self).__init__(display_name)
        self.loader, self.loadname, self.dirs = loader, name, dirs

    def reload(self):
        return self.loader(self.loadname, self.dirs)[0]


def get_template(template_name, dirs=_dirs_undefined, using=None):
    """
    Loads and returns a template for the given name.

    Raises TemplateDoesNotExist if no such template exists.
    """
    engines = _engine_list(using)
    for engine in engines:
        try:
            # This is required for deprecating the dirs argument. Simply
            # return engine.get_template(template_name) in Django 2.0.
            if isinstance(engine, DjangoTemplates):
                return engine.get_template(template_name, dirs)
            elif dirs is not _dirs_undefined:
                warnings.warn(
                    "Skipping template backend %s because its get_template "
                    "method doesn't support the dirs argument." % engine.name,
                    stacklevel=2)
            else:
                return engine.get_template(template_name)
        except TemplateDoesNotExist:
            pass

    raise TemplateDoesNotExist(template_name)


def select_template(template_name_list, dirs=_dirs_undefined, using=None):
    """
    Loads and returns a template for one of the given names.

    Tries names in order and returns the first template found.

    Raises TemplateDoesNotExist if no such template exists.
    """
    engines = _engine_list(using)
    for template_name in template_name_list:
        for engine in engines:
            try:
                # This is required for deprecating the dirs argument. Simply
                # use engine.get_template(template_name) in Django 2.0.
                if isinstance(engine, DjangoTemplates):
                    return engine.get_template(template_name, dirs)
                elif dirs is not _dirs_undefined:
                    warnings.warn(
                        "Skipping template backend %s because its get_template "
                        "method doesn't support the dirs argument." % engine.name,
                        stacklevel=2)
                else:
                    return engine.get_template(template_name)
            except TemplateDoesNotExist:
                pass

    if template_name_list:
        raise TemplateDoesNotExist(', '.join(template_name_list))
    else:
        raise TemplateDoesNotExist("No template names provided")


def render_to_string(*args, **kwargs):
    return Engine.get_default().render_to_string(*args, **kwargs)


def _engine_list(using=None):
    return engines.all() if using is None else [engines[using]]


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
