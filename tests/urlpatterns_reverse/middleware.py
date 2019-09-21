from django.http import HttpResponse, StreamingHttpResponse
from django.urls import reverse

from . import urlconf_inner


class MiddlewareMixin:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)


class ChangeURLconfMiddleware(MiddlewareMixin):
    def __call__(self, request):
        request.urlconf = urlconf_inner.__name__
        return self.get_response(request)


class NullChangeURLconfMiddleware(MiddlewareMixin):
    def __call__(self, request):
        request.urlconf = None
        return self.get_response(request)


class ReverseInnerInResponseMiddleware(MiddlewareMixin):
    def __call__(self, request):
        self.get_response(request)
        return HttpResponse(reverse('inner'))


class ReverseOuterInResponseMiddleware(MiddlewareMixin):
    def __call__(self, request):
        self.get_response(request)
        return HttpResponse(reverse('outer'))


class ReverseInnerInStreaming(MiddlewareMixin):
    def process_view(self, *args, **kwargs):
        def stream():
            yield reverse('inner')
        return StreamingHttpResponse(stream())


class ReverseOuterInStreaming(MiddlewareMixin):
    def process_view(self, *args, **kwargs):
        def stream():
            yield reverse('outer')
        return StreamingHttpResponse(stream())
