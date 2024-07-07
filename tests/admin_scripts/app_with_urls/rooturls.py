from django.urls import include, path

urlpatterns = [
    path("namespaced/", include("admin_scripts.app_with_urls.urls", namespace="ns")),
    path("nons/", include("admin_scripts.app_with_urls.urls")),
]
