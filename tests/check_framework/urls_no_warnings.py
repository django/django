from django.conf.urls import include, url
from django.http import HttpResponse


def view(request):
    return HttpResponse('')


urlpatterns = [
    url(r'^foo/', view, name='foo'),
    # This dollar is ok as it is escaped
    url(r'^\$', include([
        url(r'^bar/$', view, name='bar'),
    ])),
]
