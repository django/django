from django.conf.urls import url


def some_view(request):
    pass


urlpatterns = [
    url(r'^some-url/$', some_view, name='some-view'),
]
