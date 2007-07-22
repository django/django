"""
This module collects helper functions and classes that "span" multiple levels
of MVC. In other words, these functions/classes introduce controlled coupling
for convenience's sake.
"""

from django.template import loader
from django.http import HttpResponse, Http404
from django.db.models.manager import Manager

def render_to_response(*args, **kwargs):
    """
    Return a HttpResponse whose content is filled with the result of calling
    django.template.loader.render_to_string() with the passed arguments.
    """
    return HttpResponse(loader.render_to_string(*args, **kwargs))
load_and_render = render_to_response # For backwards compatibility.

def get_object_or_404(klass, *args, **kwargs):
    """
    Use get() to return an object, or raise a Http404 exception if the object
    does not exist.

    klass may be a Model or Manager object.  All other passed
    arguments and keyword arguments are used in the get() query.

    Note: Like with get(), an AssertionError will be raised if more than one
    object is found.
    """
    if isinstance(klass, Manager):
        manager = klass
        klass = manager.model
    else:
        manager = klass._default_manager
    try:
        return manager.get(*args, **kwargs)
    except klass.DoesNotExist:
        raise Http404('No %s matches the given query.' % klass._meta.object_name)

def get_list_or_404(klass, *args, **kwargs):
    """
    Use filter() to return a list of objects, or raise a Http404 exception if
    the list is empty.

    klass may be a Model or Manager object.  All other passed
    arguments and keyword arguments are used in the filter() query.
    """
    if isinstance(klass, Manager):
        manager = klass
    else:
        manager = klass._default_manager
    obj_list = list(manager.filter(*args, **kwargs))
    if not obj_list:
        raise Http404('No %s matches the given query.' % manager.model._meta.object_name)
    return obj_list
