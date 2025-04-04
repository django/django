"""
This module collects helper functions and classes that "span" multiple levels
of MVC. In other words, these functions/classes introduce controlled coupling
for convenience's sake.
"""

from django.http import (
    Http404,
    HttpResponse,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
)
from django.template import loader
from django.urls import NoReverseMatch, reverse
from django.utils.functional import Promise


def render(
    request, template_name, context=None, content_type=None, status=None, using=None
):
    """
    Return an HttpResponse whose content is filled with the result of calling
    django.template.loader.render_to_string() with the passed arguments.
    """
    content = loader.render_to_string(template_name, context, request, using=using)
    return HttpResponse(content, content_type, status)


def redirect(to, *args, permanent=False, preserve_request=False, **kwargs):
    """
    Return an HttpResponseRedirect to the appropriate URL for the arguments
    passed.

    The arguments could be:

        * A model: the model's `get_absolute_url()` function will be called.

        * A view name, possibly with arguments: `urls.reverse()` will be used
          to reverse-resolve the name.

        * A URL, which will be used as-is for the redirect location.

    Issues a temporary redirect by default. Set permanent=True to issue a
    permanent redirect. Set preserve_request=True to instruct the user agent
    to preserve the original HTTP method and body when following the redirect.
    """
    redirect_class = (
        HttpResponsePermanentRedirect if permanent else HttpResponseRedirect
    )
    return redirect_class(
        resolve_url(to, *args, **kwargs),
        preserve_request=preserve_request,
    )


def _get_queryset(klass):
    """
    Return a QuerySet or a Manager.
    Duck typing in action: any class with a `get()` method (for
    get_object_or_404) or a `filter()` method (for get_list_or_404) might do
    the job.
    """
    # If it is a model class or anything else with ._default_manager
    if hasattr(klass, "_default_manager"):
        return klass._default_manager.all()
    return klass


def get_object_or_404(klass, *args, **kwargs):
    """
    Use get() to return an object, or raise an Http404 exception if the object
    does not exist.

    klass may be a Model, Manager, or QuerySet object. All other passed
    arguments and keyword arguments are used in the get() query.

    Like with QuerySet.get(), MultipleObjectsReturned is raised if more than
    one object is found.
    """
    queryset = _get_queryset(klass)
    if not hasattr(queryset, "get"):
        klass__name = (
            klass.__name__ if isinstance(klass, type) else klass.__class__.__name__
        )
        raise ValueError(
            "First argument to get_object_or_404() must be a Model, Manager, "
            "or QuerySet, not '%s'." % klass__name
        )
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        raise Http404(
            "No %s matches the given query." % queryset.model._meta.object_name
        )


async def aget_object_or_404(klass, *args, **kwargs):
    """See get_object_or_404()."""
    queryset = _get_queryset(klass)
    if not hasattr(queryset, "aget"):
        klass__name = (
            klass.__name__ if isinstance(klass, type) else klass.__class__.__name__
        )
        raise ValueError(
            "First argument to aget_object_or_404() must be a Model, Manager, or "
            f"QuerySet, not '{klass__name}'."
        )
    try:
        return await queryset.aget(*args, **kwargs)
    except queryset.model.DoesNotExist:
        raise Http404(f"No {queryset.model._meta.object_name} matches the given query.")


def get_list_or_404(klass, *args, **kwargs):
    """
    Use filter() to return a list of objects, or raise an Http404 exception if
    the list is empty.

    klass may be a Model, Manager, or QuerySet object. All other passed
    arguments and keyword arguments are used in the filter() query.
    """
    queryset = _get_queryset(klass)
    if not hasattr(queryset, "filter"):
        klass__name = (
            klass.__name__ if isinstance(klass, type) else klass.__class__.__name__
        )
        raise ValueError(
            "First argument to get_list_or_404() must be a Model, Manager, or "
            "QuerySet, not '%s'." % klass__name
        )
    obj_list = list(queryset.filter(*args, **kwargs))
    if not obj_list:
        raise Http404(
            "No %s matches the given query." % queryset.model._meta.object_name
        )
    return obj_list


async def aget_list_or_404(klass, *args, **kwargs):
    """See get_list_or_404()."""
    queryset = _get_queryset(klass)
    if not hasattr(queryset, "filter"):
        klass__name = (
            klass.__name__ if isinstance(klass, type) else klass.__class__.__name__
        )
        raise ValueError(
            "First argument to aget_list_or_404() must be a Model, Manager, or "
            f"QuerySet, not '{klass__name}'."
        )
    obj_list = [obj async for obj in queryset.filter(*args, **kwargs)]
    if not obj_list:
        raise Http404(f"No {queryset.model._meta.object_name} matches the given query.")
    return obj_list


def resolve_url(to, *args, **kwargs):
    """
    Return a URL appropriate for the arguments passed.

    The arguments could be:

        * A model: the model's `get_absolute_url()` function will be called.

        * A view name, possibly with arguments: `urls.reverse()` will be used
          to reverse-resolve the name.

        * A URL, which will be returned as-is.
    """
    # If it's a model, use get_absolute_url()
    if hasattr(to, "get_absolute_url"):
        return to.get_absolute_url()

    if isinstance(to, Promise):
        # Expand the lazy instance, as it can cause issues when it is passed
        # further to some Python functions like urlparse.
        to = str(to)

    # Handle relative URLs
    if isinstance(to, str) and to.startswith(("./", "../")):
        return to

    # Next try a reverse URL resolution.
    try:
        return reverse(to, args=args, kwargs=kwargs)
    except NoReverseMatch:
        # If this is a callable, re-raise.
        if callable(to):
            raise
        # If this doesn't "feel" like a URL, re-raise.
        if "/" not in to and "." not in to:
            raise

    # Finally, fall back and assume it's a URL
    return to
