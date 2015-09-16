from django.conf.urls import include, url
from django.http import HttpResponse


def view(request):
    return HttpResponse('')


urlpatterns = [
    url('^', include([
        url(r'^$', view, name='name_with:colon'),
    ])),
]
