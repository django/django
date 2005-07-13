"""
Some pages in our CMS are served up with custom HTTP headers containing useful
information about those pages -- namely, the contenttype and object ID.

This module contains utility functions for retrieving and doing interesting
things with these special "X-Headers" (so called because the HTTP spec demands
that custom headers are prefxed with "X-".)

Next time you're at slashdot.org, watch out for X-Fry and X-Bender. :)
"""

def populate_xheaders(request, response, package, python_module_name, object_id):
    """
    Adds the "X-Object-Type" and "X-Object-Id" headers to the given
    HttpResponse according to the given package, python_module_name and
    object_id -- but only if the given HttpRequest object has an IP address
    within the INTERNAL_IPS setting.
    """
    from django.conf.settings import INTERNAL_IPS
    if request.META['REMOTE_ADDR'] in INTERNAL_IPS:
        response['X-Object-Type'] = "%s.%s" % (package, python_module_name)
        response['X-Object-Id'] = str(object_id)
