from django.core.exceptions import ObjectDoesNotExist
from django.template import Context, RequestContext, loader
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django import http

def shortcut(request, content_type_id, object_id):
    "Redirect to an object's page based on a content-type ID and an object ID."
    # Look up the object, making sure it's got a get_absolute_url() function.
    try:
        content_type = ContentType.objects.get(pk=content_type_id)
        obj = content_type.get_object_for_this_type(pk=object_id)
    except ObjectDoesNotExist:
        raise http.Http404, "Content type %s object %s doesn't exist" % (content_type_id, object_id)
    try:
        absurl = obj.get_absolute_url()
    except AttributeError:
        raise http.Http404, "%s objects don't have get_absolute_url() methods" % content_type.name

    # Try to figure out the object's domain, so we can do a cross-site redirect
    # if necessary.

    # If the object actually defines a domain, we're done.
    if absurl.startswith('http://') or absurl.startswith('https://'):
        return http.HttpResponseRedirect(absurl)

    object_domain = None

    # Otherwise, we need to introspect the object's relationships for a
    # relation to the Site object
    opts = obj._meta

    # First, look for an many-to-many relationship to sites
    for field in opts.many_to_many:
        if field.rel.to is Site:
            try:
                object_domain = getattr(obj, field.name).all()[0].domain
            except IndexError:
                pass
            if object_domain is not None:
                break

    # Next look for a many-to-one relationship to site
    if object_domain is None:
        for field in obj._meta.fields:
            if field.rel and field.rel.to is Site:
                try:
                    object_domain = getattr(obj, field.name).domain
                except Site.DoesNotExist:
                    pass
                if object_domain is not None:
                    break

    # Fall back to the current site (if possible)
    if object_domain is None:
        try:
            object_domain = Site.objects.get_current().domain
        except Site.DoesNotExist:
            pass

    # If all that malarkey found an object domain, use it; otherwise fall back
    # to whatever get_absolute_url() returned.
    if object_domain is not None:
        protocol = request.is_secure() and 'https' or 'http'
        return http.HttpResponseRedirect('%s://%s%s' % (protocol, object_domain, absurl))
    else:
        return http.HttpResponseRedirect(absurl)

def page_not_found(request, template_name='404.html'):
    """
    Default 404 handler, which looks for the requested URL in the redirects
    table, redirects if found, and displays 404 page if not redirected.

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
