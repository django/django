from django.urls import include, path, register_converter

from . import converters, views

register_converter(converters.Base64Converter, "base64")

subsubpatterns = [
    path("<base64:last_value>/", views.empty_view, name="subsubpattern-base64"),
]

subpatterns = [
    path("<base64:value>/", views.empty_view, name="subpattern-base64"),
    path(
        "<base64:value>/",
        include(
            (subsubpatterns, "second-layer-namespaced-base64"), "instance-ns-base64"
        ),
    ),
]

urlpatterns = [
    path("base64/<base64:value>/", views.empty_view, name="base64"),
    path("base64/<base64:base>/subpatterns/", include(subpatterns)),
    path(
        "base64/<base64:base>/namespaced/", include((subpatterns, "namespaced-base64"))
    ),
]
