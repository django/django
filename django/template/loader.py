import warnings

from django.utils.deprecation import RemovedInDjango110Warning

from . import engines
from .backends.django import DjangoTemplates
from .base import Origin, TemplateDoesNotExist
from .engine import (
    _context_instance_undefined, _dictionary_undefined, _dirs_undefined,
)
from .loaders import base


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
            # return engine.get_template(template_name) in Django 1.10.
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
                # use engine.get_template(template_name) in Django 1.10.
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


def render_to_string(template_name, context=None,
                     context_instance=_context_instance_undefined,
                     dirs=_dirs_undefined,
                     dictionary=_dictionary_undefined,
                     request=None, using=None):
    """
    Loads a template and renders it with a context. Returns a string.

    template_name may be a string or a list of strings.
    """
    if (context_instance is _context_instance_undefined
            and dirs is _dirs_undefined
            and dictionary is _dictionary_undefined):
        # No deprecated arguments were passed - use the new code path
        if isinstance(template_name, (list, tuple)):
            template = select_template(template_name, using=using)
        else:
            template = get_template(template_name, using=using)
        return template.render(context, request)

    else:
        # Some deprecated arguments were passed - use the legacy code path
        for engine in _engine_list(using):
            try:
                # This is required for deprecating properly arguments specific
                # to Django templates. Remove Engine.render_to_string() at the
                # same time as this code path in Django 1.10.
                if isinstance(engine, DjangoTemplates):
                    if request is not None:
                        raise ValueError(
                            "render_to_string doesn't support the request argument "
                            "when some deprecated arguments are passed.")
                    # Hack -- use the internal Engine instance of DjangoTemplates.
                    return engine.engine.render_to_string(
                        template_name, context, context_instance, dirs, dictionary)
                elif context_instance is not _context_instance_undefined:
                    warnings.warn(
                        "Skipping template backend %s because its render_to_string "
                        "method doesn't support the context_instance argument." %
                        engine.name, stacklevel=2)
                elif dirs is not _dirs_undefined:
                    warnings.warn(
                        "Skipping template backend %s because its render_to_string "
                        "method doesn't support the dirs argument." % engine.name,
                        stacklevel=2)
                elif dictionary is not _dictionary_undefined:
                    warnings.warn(
                        "Skipping template backend %s because its render_to_string "
                        "method doesn't support the dictionary argument." %
                        engine.name, stacklevel=2)
            except TemplateDoesNotExist:
                continue

        if template_name:
            if isinstance(template_name, (list, tuple)):
                template_name = ', '.join(template_name)
            raise TemplateDoesNotExist(template_name)
        else:
            raise TemplateDoesNotExist("No template names provided")


def _engine_list(using=None):
    return engines.all() if using is None else [engines[using]]


class BaseLoader(base.Loader):
    _accepts_engine_in_init = False

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "django.template.loader.BaseLoader was superseded by "
            "django.template.loaders.base.Loader.",
            RemovedInDjango110Warning, stacklevel=2)
        super(BaseLoader, self).__init__(*args, **kwargs)
