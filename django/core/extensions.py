# This module collects helper functions and classes that "span" multiple levels
# of MVC. In other words, these functions/classes introduce controlled coupling
# for convenience's sake.

from django.core.exceptions import Http404, ImproperlyConfigured, ObjectDoesNotExist
from django.core.template import Context, loader
from django.conf.settings import TEMPLATE_CONTEXT_PROCESSORS
from django.utils.httpwrappers import HttpResponse

_standard_context_processors = None

# This is a function rather than module-level procedural code because we only
# want it to execute if somebody uses DjangoContext.
def get_standard_processors():
    global _standard_context_processors
    if _standard_context_processors is None:
        processors = []
        for path in TEMPLATE_CONTEXT_PROCESSORS:
            i = path.rfind('.')
            module, attr = path[:i], path[i+1:]
            try:
                mod = __import__(module, '', '', [attr])
            except ImportError, e:
                raise ImproperlyConfigured, 'Error importing request processor module %s: "%s"' % (module, e)
            try:
                func = getattr(mod, attr)
            except AttributeError:
                raise ImproperlyConfigured, 'Module "%s" does not define a "%s" callable request processor' % (module, attr)
            processors.append(func)
        _standard_context_processors = tuple(processors)
    return _standard_context_processors

def render_to_response(*args, **kwargs):
    return HttpResponse(loader.render_to_string(*args, **kwargs))
load_and_render = render_to_response # For backwards compatibility.

def get_object_or_404(mod, **kwargs):
    try:
        return mod.get_object(**kwargs)
    except ObjectDoesNotExist:
        raise Http404

def get_list_or_404(mod, **kwargs):
    obj_list = mod.get_list(**kwargs)
    if not obj_list:
        raise Http404
    return obj_list

class DjangoContext(Context):
    """
    This subclass of template.Context automatically populates itself using
    the processors defined in TEMPLATE_CONTEXT_PROCESSORS.
    Additional processors can be specified as a list of callables
    using the "processors" keyword argument.
    """
    def __init__(self, request, dict=None, processors=None):
        Context.__init__(self, dict)
        if processors is None:
            processors = ()
        else:
            processors = tuple(processors)
        for processor in get_standard_processors() + processors:
            self.update(processor(request))

# PermWrapper and PermLookupDict proxy the permissions system into objects that
# the template system can understand.

class PermLookupDict:
    def __init__(self, user, module_name):
        self.user, self.module_name = user, module_name
    def __repr__(self):
        return str(self.user.get_permission_list())
    def __getitem__(self, perm_name):
        return self.user.has_perm("%s.%s" % (self.module_name, perm_name))
    def __nonzero__(self):
        return self.user.has_module_perms(self.module_name)

class PermWrapper:
    def __init__(self, user):
        self.user = user
    def __getitem__(self, module_name):
        return PermLookupDict(self.user, module_name)
