from django.core import template_loader
from django.core.exceptions import Http404, ObjectDoesNotExist
from django.core.extensions import CMSContext as Context
from django.models.core import sites
from django.utils import httpwrappers

def shortcut(request, content_type_id, object_id):
    from django.models.core import contenttypes
    try:
        content_type = contenttypes.get_object(id__exact=content_type_id)
        obj = content_type.get_object_for_this_type(id__exact=object_id)
    except ObjectDoesNotExist:
        raise Http404, "Content type %s object %s doesn't exist" % (content_type_id, object_id)
    if not hasattr(obj, 'get_absolute_url'):
        raise Http404, "%s objects don't have get_absolute_url() methods" % content_type.name
    object_domain = None
    if hasattr(obj, 'get_site_list'):
        site_list = obj.get_site_list()
        if site_list:
            object_domain = site_list[0].domain
    elif hasattr(obj, 'get_site'):
        try:
            object_domain = obj.get_site().domain
        except sites.SiteDoesNotExist:
            pass
    try:
        object_domain = sites.get_current().domain
    except sites.SiteDoesNotExist:
        pass
    if not object_domain:
        return httpwrappers.HttpResponseRedirect(obj.get_absolute_url())
    return httpwrappers.HttpResponseRedirect('http://%s%s' % (object_domain, obj.get_absolute_url()))

def page_not_found(request):
    """
    Default 404 handler, which looks for the requested URL in the redirects
    table, redirects if found, and displays 404 page if not redirected.

    Templates: `404`
    Context: None
    """
    from django.models.core import redirects
    from django.conf.settings import APPEND_SLASH, SITE_ID
    path = request.get_full_path()
    try:
        r = redirects.get_object(site_id__exact=SITE_ID, old_path__exact=path)
    except redirects.RedirectDoesNotExist:
        r = None
    if r is None and APPEND_SLASH:
        # Try removing the trailing slash.
        try:
            r = redirects.get_object(site_id__exact=SITE_ID, old_path__exact=path[:path.rfind('/')]+path[path.rfind('/')+1:])
        except redirects.RedirectDoesNotExist:
            pass
    if r is not None:
        if r == '':
            return httpwrappers.HttpResponseGone()
        return httpwrappers.HttpResponseRedirect(r.new_path)
    t = template_loader.get_template('404')
    c = Context(request)
    return httpwrappers.HttpResponseNotFound(t.render(c))

def server_error(request):
    """
    500 Error handler

    Templates: `500`
    Context: None
    """
    t = template_loader.get_template('500')
    c = Context(request)
    return httpwrappers.HttpResponseServerError(t.render(c))
