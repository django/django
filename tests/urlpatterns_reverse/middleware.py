from __future__ import absolute_import

from django.core.urlresolvers import reverse
from django.http import HttpResponse, StreamingHttpResponse

from . import urlconf_inner


class ChangeURLconfMiddleware(object):
    def process_request(self, request):
        request.urlconf = urlconf_inner.__name__

class NullChangeURLconfMiddleware(object):
    def process_request(self, request):
        request.urlconf = None

class ReverseInnerInResponseMiddleware(object):
    def process_response(self, *args, **kwargs):
        return HttpResponse(reverse('inner'))

class ReverseOuterInResponseMiddleware(object):
    def process_response(self, *args, **kwargs):
        return HttpResponse(reverse('outer'))

class ReverseInnerInStreaming(object):
    def process_view(self, *args, **kwargs):
        def stream():
            yield reverse('inner')
        return StreamingHttpResponse(stream())

class ReverseOuterInStreaming(object):
    def process_view(self, *args, **kwargs):
        def stream():
            yield reverse('outer')
        return StreamingHttpResponse(stream())
