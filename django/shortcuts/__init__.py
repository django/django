"""
This module collects helper functions and classes that "span" multiple levels
of MVC. In other words, these functions/classes introduce controlled coupling
for convenience's sake.
"""

from django.template import loader
from django.http import HttpResponse, Http404
from django.db.models.manager import Manager
from django.db.models.query import QuerySet

def render_to_response(*args, **kwargs):
    """
    Returns a HttpResponse whose content is filled with the result of calling
    django.template.loader.render_to_string() with the passed arguments.
    """
    httpresponse_kwargs = {'mimetype': kwargs.pop('mimetype', None)}
    return HttpResponse(loader.render_to_string(*args, **kwargs), **httpresponse_kwargs)

def _get_queryset(klass):
    """
    Returns a QuerySet from a Model, Manager, or QuerySet. Created to make
    get_object_or_404 and get_list_or_404 more DRY.
    """
    if isinstance(klass, QuerySet):
        return klass
    elif isinstance(klass, Manager):
        manager = klass
    else:
        manager = klass._default_manager
    return manager.all()

def get_object_or_404(klass, *args, **kwargs):
    """
    Uses get() to return an object, or raises a Http404 exception if the object
    does not exist.

    klass may be a Model, Manager, or QuerySet object. All other passed
    arguments and keyword arguments are used in the get() query.

    Note: Like with get(), an MultipleObjectsReturned will be raised if more than one
    object is found.
    """
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        raise Http404('No %s matches the given query.' % queryset.model._meta.object_name)

def get_list_or_404(klass, *args, **kwargs):
    """
    Uses filter() to return a list of objects, or raise a Http404 exception if
    the list is empty.

    klass may be a Model, Manager, or QuerySet object. All other passed
    arguments and keyword arguments are used in the filter() query.
    """
    queryset = _get_queryset(klass)
    obj_list = list(queryset.filter(*args, **kwargs))
    if not obj_list:
        raise Http404('No %s matches the given query.' % queryset.model._meta.object_name)
    return obj_list
