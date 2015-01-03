from django.conf.urls import url
from django.http import HttpResponse, FileResponse


def helloworld(request):
    return HttpResponse("Hello World!")

urlpatterns = [
    url("^$", helloworld),
    url(r'^file/$', lambda x: FileResponse(open(__file__, 'rb'))),
]
