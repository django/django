from django.contrib import admin
from django.urls import include, path

from . import views

backend_urls = (
    [
        path("something/", views.XViewClass.as_view(), name="something"),
    ],
    "backend",
)

urlpatterns = [
    path("admin/doc/", include("django.contrib.admindocs.urls")),
    path("admin/", admin.site.urls),
    path("api/backend/", include(backend_urls, namespace="backend")),
]
