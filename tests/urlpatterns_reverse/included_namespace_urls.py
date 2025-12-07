from django.urls import include, path, re_path

from .utils import URLObject
from .views import empty_view, view_class_instance

testobj3 = URLObject("testapp", "test-ns3")
testobj4 = URLObject("testapp", "test-ns4")

app_name = "included_namespace_urls"
urlpatterns = [
    path("normal/", empty_view, name="inc-normal-view"),
    re_path(
        "^normal/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$",
        empty_view,
        name="inc-normal-view",
    ),
    re_path(r"^\+\\\$\*/$", empty_view, name="inc-special-view"),
    re_path(
        "^mixed_args/([0-9]+)/(?P<arg2>[0-9]+)/$", empty_view, name="inc-mixed-args"
    ),
    re_path("^no_kwargs/([0-9]+)/([0-9]+)/$", empty_view, name="inc-no-kwargs"),
    re_path(
        "^view_class/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$",
        view_class_instance,
        name="inc-view-class",
    ),
    path("test3/", include(*testobj3.urls)),
    path("test4/", include(*testobj4.urls)),
    path(
        "ns-included3/",
        include(
            ("urlpatterns_reverse.included_urls", "included_urls"), namespace="inc-ns3"
        ),
    ),
    path(
        "ns-included4/",
        include("urlpatterns_reverse.namespace_urls", namespace="inc-ns4"),
    ),
]
