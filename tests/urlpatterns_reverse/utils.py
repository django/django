from django.urls import path, re_path

from . import views


class URLObject:
    urlpatterns = [
        path("inner/", views.empty_view, name="urlobject-view"),
        re_path(
            r"^inner/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$",
            views.empty_view,
            name="urlobject-view",
        ),
        re_path(r"^inner/\+\\\$\*/$", views.empty_view, name="urlobject-special-view"),
    ]

    def __init__(self, app_name, namespace=None):
        self.app_name = app_name
        self.namespace = namespace

    @property
    def urls(self):
        return (self.urlpatterns, self.app_name), self.namespace

    @property
    def app_urls(self):
        return self.urlpatterns, self.app_name
