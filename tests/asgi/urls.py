from django.http import FileResponse, HttpResponse
from django.urls import path


def hello(request):
    name = request.query_params.get('name') or 'World'
    return HttpResponse('Hello %s!' % name)


def hello_meta(request):
    return HttpResponse(
        'From %s' % request.meta.get('HTTP_REFERER') or '',
        content_type=request.meta.get('CONTENT_TYPE'),
    )


test_filename = __file__


urlpatterns = [
    path('', hello),
    path('file/', lambda x: FileResponse(open(test_filename, 'rb'))),
    path('meta/', hello_meta),
]
