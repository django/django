import warnings

from django.conf import settings
from django.template.base import Origin, Template, Context, TemplateDoesNotExist
from django.template.loaders.utils import get_template_loaders
from django.utils.deprecation import RemovedInDjango20Warning


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


def find_template(name, dirs=None):
    for loader in get_template_loaders():
        try:
            source, display_name = loader(name, dirs)
            return (source, make_origin(display_name, loader, name, dirs))
        except TemplateDoesNotExist:
            pass
    raise TemplateDoesNotExist(name)


def get_template(template_name, dirs=None):
    """
    Returns a compiled Template object for the given template name,
    handling template inheritance recursively.
    """
    template, origin = find_template(template_name, dirs)
    if not hasattr(template, 'render'):
        # template needs to be compiled
        template = get_template_from_string(template, origin, template_name)
    return template


def get_template_from_string(source, origin=None, name=None):
    """
    Returns a compiled Template object for the given template code,
    handling template inheritance recursively.
    """
    return Template(source, origin, name)


def render_to_string(template_name, dictionary=None, context_instance=None,
                     dirs=None):
    """
    Loads the given template_name and renders it with the given dictionary as
    context. The template_name may be a string to load a single template using
    get_template, or it may be a tuple to use select_template to find one of
    the templates in the list. Returns a string.
    """
    if isinstance(template_name, (list, tuple)):
        t = select_template(template_name, dirs)
    else:
        t = get_template(template_name, dirs)
    if not context_instance:
        return t.render(Context(dictionary))
    if not dictionary:
        return t.render(context_instance)
    # Add the dictionary to the context stack, ensuring it gets removed again
    # to keep the context_instance in the same state it started in.
    with context_instance.push(dictionary):
        return t.render(context_instance)


def select_template(template_name_list, dirs=None):
    "Given a list of template names, returns the first that can be loaded."
    if not template_name_list:
        raise TemplateDoesNotExist("No template names provided")
    not_found = []
    for template_name in template_name_list:
        try:
            return get_template(template_name, dirs)
        except TemplateDoesNotExist as e:
            if e.args[0] not in not_found:
                not_found.append(e.args[0])
            continue
    # If we get here, none of the templates could be loaded
    raise TemplateDoesNotExist(', '.join(not_found))


# This line must remain at the bottom to avoid import loops.
from .loaders import base


class BaseLoader(base.Loader):

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "django.template.loader.BaseLoader was renamed to "
            "django.template.loaders.base.Loader.",
            RemovedInDjango20Warning, stacklevel=2)
        super(BaseLoader, self).__init__(*args, **kwargs)
