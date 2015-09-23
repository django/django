from django.conf.urls import include, url

urlpatterns = [
    url('^', include([
        url(r'/starting-with-slash/$', lambda x: x),
    ])),
]
