from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.urls import path


def helloworld(request):
    return HttpResponse("Hello World!")


def cookie(request):
    response = HttpResponse("Hello World!")
    response.set_cookie("key", "value")
    return response


def streaming(request):
    def gen():
        yield b"Hello "
        yield b"Streaming!"

    return StreamingHttpResponse(gen())


urlpatterns = [
    path("", helloworld),
    path("cookie/", cookie),
    path("file/", lambda x: FileResponse(open(__file__, "rb"))),
    path("streaming/", streaming),
]
