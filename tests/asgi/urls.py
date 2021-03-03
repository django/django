from contextvars import ContextVar

from django.http import FileResponse, HttpResponse, ServerSentEventsResponse
from django.urls import path


def hello(request):
    name = request.GET.get('name') or 'World'
    return HttpResponse('Hello %s!' % name)


def hello_meta(request):
    return HttpResponse(
        'From %s' % request.META.get('HTTP_REFERER') or '',
        content_type=request.META.get('CONTENT_TYPE'),
    )


message_broker = ContextVar('message_broker')


async def server_sent_events_view(request):
    _message_broker = message_broker.get()
    return ServerSentEventsResponse(_message_broker.get, last_event_id=request.headers.get('Last-Event-ID', 0))


test_filename = __file__

urlpatterns = [
    path('', hello),
    path('file/', lambda x: FileResponse(open(test_filename, 'rb'))),
    path('meta/', hello_meta),
    path('sse/', server_sent_events_view),
]
