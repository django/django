from django.conf.urls import include, url
from django.http import HttpResponse


def view(request):
    return HttpResponse('')


urlpatterns = [
    url('^', include([
        url(r'/starting-with-slash/$', view),
    ])),
]
