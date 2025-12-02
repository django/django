from django.http import FileResponse, HttpResponse
from django.urls import path


def helloworld(request):
    return HttpResponse("Hello World!")


def cookie(request):
    response = HttpResponse("Hello World!")
    response.set_cookie("key", "value")
    return response


def file_view(request):
    return FileResponse(open(__file__, "rb"))


urlpatterns = [
    path("", helloworld),
    path("cookie/", cookie),
    path("file/", file_view),
]
