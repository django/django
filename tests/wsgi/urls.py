from django.conf.urls import url
from django.http import HttpResponse


def helloworld(request):
    return HttpResponse("Hello World!")

urlpatterns = [
    url("^$", helloworld),
]
