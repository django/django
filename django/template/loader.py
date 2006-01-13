# Wrapper for loading templates from storage of some sort (e.g. filesystem, database).
#
# This uses the TEMPLATE_LOADERS setting, which is a list of loaders to use.
# Each loader is expected to have this interface:
#
#    callable(name, dirs=[])
#
# name is the template name.
# dirs is an optional list of directories to search instead of TEMPLATE_DIRS.
#
# The loader should return a tuple of (template_source, path). The path returned
# might be shown to the user for debugging purposes, so it should identify where
# the template was loaded from.
#
# Each loader should have an "is_usable" attribute set. This is a boolean that
# specifies whether the loader can be used in this Python installation. Each
# loader is responsible for setting this when it's initialized.
#
# For example, the eggs loader (which is capable of loading templates from
# Python eggs) sets is_usable to False if the "pkg_resources" module isn't
# installed, because pkg_resources is necessary to read eggs.

from django.core.exceptions import ImproperlyConfigured
from django.template import Origin, StringOrigin, Template, Context, TemplateDoesNotExist, add_to_builtins
from django.conf.settings import TEMPLATE_LOADERS
from django.conf import settings

template_source_loaders = []
for path in TEMPLATE_LOADERS:
    i = path.rfind('.')
    module, attr = path[:i], path[i+1:]
    try:
        mod = __import__(module, globals(), locals(), [attr])
    except ImportError, e:
        raise ImproperlyConfigured, 'Error importing template source loader %s: "%s"' % (module, e)
    try:
        func = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured, 'Module "%s" does not define a "%s" callable template source loader' % (module, attr)
    if not func.is_usable:
        import warnings
        warnings.warn("Your TEMPLATE_LOADERS setting includes %r, but your Python installation doesn't support that type of template loading. Consider removing that line from TEMPLATE_LOADERS." % path)
    else:
        template_source_loaders.append(func)

class LoaderOrigin(Origin):
    def __init__(self, display_name, loader, name, dirs):
        super(LoaderOrigin, self).__init__(display_name)
        self.loader, self.loadname, self.dirs = loader, name, dirs

    def reload(self):
        return self.loader(self.loadname, self.dirs)[0]

def make_origin(display_name, loader, name, dirs):
    if settings.TEMPLATE_DEBUG:
        return LoaderOrigin(display_name, loader, name, dirs)
    else:
        return None

def find_template_source(name, dirs=None):
    for loader in template_source_loaders:
        try:
            source, display_name = loader(name, dirs)
            return (source, make_origin(display_name, loader, name, dirs))
        except TemplateDoesNotExist:
            pass
    raise TemplateDoesNotExist, name

def get_template(template_name):
    """
    Returns a compiled Template object for the given template name,
    handling template inheritance recursively.
    """
    return get_template_from_string(*find_template_source(template_name))

def get_template_from_string(source, origin=None ):
    """
    Returns a compiled Template object for the given template code,
    handling template inheritance recursively.
    """
    return Template(source, origin)

def render_to_string(template_name, dictionary=None, context_instance=None):
    """
    Loads the given template_name and renders it with the given dictionary as
    context. The template_name may be a string to load a single template using
    get_template, or it may be a tuple to use select_template to find one of
    the templates in the list. Returns a string.
    """
    dictionary = dictionary or {}
    if isinstance(template_name, (list, tuple)):
        t = select_template(template_name)
    else:
        t = get_template(template_name)
    if context_instance:
        context_instance.update(dictionary)
    else:
        context_instance = Context(dictionary)
    return t.render(context_instance)

def select_template(template_name_list):
    "Given a list of template names, returns the first that can be loaded."
    for template_name in template_name_list:
        try:
            return get_template(template_name)
        except TemplateDoesNotExist:
            continue
    # If we get here, none of the templates could be loaded
    raise TemplateDoesNotExist, ', '.join(template_name_list)

add_to_builtins('django.template.loader_tags')
