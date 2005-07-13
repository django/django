from django.core import template_loader
from django.core.exceptions import Http404
from django.core.extensions import CMSContext as Context
from django.models.core import flatfiles
from django.utils.httpwrappers import HttpResponse
from django.conf.settings import SITE_ID

def flat_file(request, url):
    """
    Flat file view

    Models: `core.flatfiles`
    Templates: Uses the template defined by the ``template_name`` field,
        or `flatfiles/default` if template_name is not defined.
    Context:
        flatfile
            `flatfiles.flatfiles` object
    """
    if not url.startswith('/'):
        url = "/" + url
    try:
        f = flatfiles.get_object(url__exact=url, sites__id__exact=SITE_ID)
    except flatfiles.FlatFileDoesNotExist:
        raise Http404
    # If registration is required for accessing this page, and the user isn't
    # logged in, redirect to the login page.
    if request.user.is_anonymous() and f.registration_required:
        from django.views.auth.login import redirect_to_login
        return redirect_to_login(request.path)
    t = template_loader.select_template([f.template_name, 'flatfiles/default'])
    c = Context(request, {
        'flatfile': f,
    })
    return HttpResponse(t.render(c))
