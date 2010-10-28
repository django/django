from django import http
from django.template import Context, RequestContext, loader

def page_not_found(request, template_name='404.html'):
    """
    Default 404 handler.

    Templates: `404.html`
    Context:
        request_path
            The path of the requested URL (e.g., '/app/pages/bad_page/')
    """
    t = loader.get_template(template_name) # You need to create a 404.html template.
    return http.HttpResponseNotFound(t.render(RequestContext(request, {'request_path': request.path})))

def server_error(request, template_name='500.html'):
    """
    500 error handler.

    Templates: `500.html`
    Context: None
    """
    t = loader.get_template(template_name) # You need to create a 500.html template.
    return http.HttpResponseServerError(t.render(Context({})))

def shortcut(request, content_type_id, object_id):
    # TODO: Remove this in Django 2.0.
    # This is a legacy view that depends on the contenttypes framework.
    # The core logic was moved to django.contrib.contenttypes.views after
    # Django 1.0, but this remains here for backwards compatibility.
    # Note that the import is *within* this function, rather than being at
    # module level, because we don't want to assume people have contenttypes
    # installed.
    from django.contrib.contenttypes.views import shortcut as real_shortcut
    return real_shortcut(request, content_type_id, object_id)
