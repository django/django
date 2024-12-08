from django.urls import include, path

common_url_patterns = (
    [
        path("app-ns1/", include([])),
        path("app-url/", include([])),
    ],
    "app-ns1",
)

urlpatterns = [
    path("app-ns1-0/", include(common_url_patterns)),
    path("app-ns1-1/", include(common_url_patterns)),
    path("app-some-url/", include(([], "app"), namespace="app-1")),
    path("app-some-url-2/", include(([], "app"), namespace="app-1")),
]
