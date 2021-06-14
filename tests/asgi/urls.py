from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.urls import path
from django.utils.asyncio import async_unsafe


def hello(request):
    name = request.GET.get('name') or 'World'
    return HttpResponse('Hello %s!' % name)


def hello_meta(request):
    return HttpResponse(
        'From %s' % request.META.get('HTTP_REFERER') or '',
        content_type=request.META.get('CONTENT_TYPE'),
    )


def streaming_view(request):
    @async_unsafe
    def async_unsafe_function():
        return True

    def generate():
        # Response iterators should be run in a sync context so functions that
        # are sync unsafe like database calls can be used.
        async_unsafe_function()

        yield "Hello World!"

    return StreamingHttpResponse(
        generate(),
        content_type="text/plain"
    )


test_filename = __file__


urlpatterns = [
    path('', hello),
    path('file/', lambda x: FileResponse(open(test_filename, 'rb'))),
    path('meta/', hello_meta),
    path('streaming/', streaming_view),
]
