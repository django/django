from django.urls import path, re_path

from .views import empty_view

urlpatterns = [
    # No kwargs
    path("conflict/cannot-go-here/", empty_view, name="name-conflict"),
    path("conflict/", empty_view, name="name-conflict"),
    # One kwarg
    re_path(r"^conflict-first/(?P<first>\w+)/$", empty_view, name="name-conflict"),
    re_path(
        r"^conflict-cannot-go-here/(?P<middle>\w+)/$", empty_view, name="name-conflict"
    ),
    re_path(r"^conflict-middle/(?P<middle>\w+)/$", empty_view, name="name-conflict"),
    re_path(r"^conflict-last/(?P<last>\w+)/$", empty_view, name="name-conflict"),
    # Two kwargs
    re_path(
        r"^conflict/(?P<another>\w+)/(?P<extra>\w+)/cannot-go-here/$",
        empty_view,
        name="name-conflict",
    ),
    re_path(
        r"^conflict/(?P<extra>\w+)/(?P<another>\w+)/$", empty_view, name="name-conflict"
    ),
]
