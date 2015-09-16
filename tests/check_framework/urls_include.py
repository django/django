from django.conf.urls import include, url

urlpatterns = [
    url(r'^', include([
        url(r'^include-with-dollar$', include([])),
    ])),
]
