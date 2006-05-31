# This module collects helper functions and classes that "span" multiple levels
# of MVC. In other words, these functions/classes introduce controlled coupling
# for convenience's sake.

from django.template import loader
from django.http import HttpResponse, Http404


def render_to_response(*args, **kwargs):
    return HttpResponse(loader.render_to_string(*args, **kwargs))
load_and_render = render_to_response # For backwards compatibility.

def get_object_or_404(klass, *args, **kwargs):
    try:
        return klass._default_manager.get(*args, **kwargs)
    except klass.DoesNotExist:
        raise Http404

def get_list_or_404(klass, **kwargs):
    obj_list = list(klass._default_manager.filter(**kwargs))
    if not obj_list:
        raise Http404
    return obj_list
