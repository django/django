from django.http import HttpResponse
from django.urls import path


def empty_response(request):
    return HttpResponse()


urlpatterns = [
    path("middleware_urlconf_view/", empty_response, name="middleware_urlconf_view"),
]
