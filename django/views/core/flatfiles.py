from django.core import template_loader
from django.core.extensions import get_object_or_404, DjangoContext
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
    f = get_object_or_404(flatfiles, url__exact=url, sites__id__exact=SITE_ID)
    # If registration is required for accessing this page, and the user isn't
    # logged in, redirect to the login page.
    if request.user.is_anonymous() and f.registration_required:
        from django.views.auth.login import redirect_to_login
        return redirect_to_login(request.path)
    t = template_loader.select_template([f.template_name, 'flatfiles/default'])
    c = DjangoContext(request, {
        'flatfile': f,
    })
    return HttpResponse(t.render(c))
