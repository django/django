from __future__ import unicode_literals

from django.http.request import split_domain_port
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class RequestSite(object):
    """
    A class that shares the primary interface of Site (i.e., it has
    ``domain`` and ``name`` attributes) but gets its data from a Django
    HttpRequest object rather than from a database.

    The save() and delete() methods raise NotImplementedError.
    """
    def __init__(self, request):
        host = request.get_host()
        domain, port = split_domain_port(host)
        self.domain = self.name = domain

    def __str__(self):
        return self.domain

    def save(self, force_insert=False, force_update=False):
        raise NotImplementedError('RequestSite cannot be saved.')

    def delete(self):
        raise NotImplementedError('RequestSite cannot be deleted.')
