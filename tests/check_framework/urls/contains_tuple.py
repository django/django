from django.conf.urls import include, url

urlpatterns = [
    url('^', include([
        (r'/starting-with-slash/$', lambda x: x),
    ])),
]
