"""
Pages in Django can are served up with custom HTTP headers containing useful
information about those pages -- namely, the content type and object ID.

This module contains utility functions for retrieving and doing interesting
things with these special "X-Headers" (so called because the HTTP spec demands
that custom headers are prefxed with "X-").

Next time you're at slashdot.org, watch out for X-Fry and X-Bender. :)
"""

def populate_xheaders(request, response, model, object_id):
    """
    Adds the "X-Object-Type" and "X-Object-Id" headers to the given
    HttpResponse according to the given model and object_id -- but only if the
    given HttpRequest object has an IP address within the INTERNAL_IPS setting
    or if the request is from a logged in staff member.
    """
    from django.conf import settings
    if request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS or (hasattr(request, 'user') and request.user.is_authenticated() and request.user.is_staff):
        response['X-Object-Type'] = "%s.%s" % (model._meta.app_label, model._meta.object_name.lower())
        response['X-Object-Id'] = str(object_id)
