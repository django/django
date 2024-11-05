from django.urls import include, path

urlpatterns = [
    path(
        route="nons/",
        view=include("admin_scripts.app_with_urls.urls_nons"),
    ),
    path(
        route="namespaced/",
        view=include("admin_scripts.app_with_urls.urls_namespaced", namespace="ns"),
    ),
]
