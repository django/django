from freedom.conf.urls import url
from freedom.http import HttpResponse


def helloworld(request):
    return HttpResponse("Hello World!")

urlpatterns = [
    url("^$", helloworld),
]
