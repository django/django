# This module collects helper functions and classes that "span" multiple levels
# of MVC. In other words, these functions/classes introduce controlled coupling
# for convenience's sake.

from django.template import loader
from django.http import HttpResponse, Http404


def render_to_response(*args, **kwargs):
    return HttpResponse(loader.render_to_string(*args, **kwargs))
load_and_render = render_to_response # For backwards compatibility.

def get_object_or_404(klass, **kwargs):
    try:
        return klass._default_manager.get_object(**kwargs)
    except klass.DoesNotExist:
        raise Http404

def get_list_or_404(klass, **kwargs):
    obj_list = klass._default_manager.get_list(**kwargs)
    if not obj_list:
        raise Http404
    return obj_list

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
