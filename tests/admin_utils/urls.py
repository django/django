from django.urls import path

from .admin import site, custom_site

urlpatterns = [
    path("test_admin/admin/", site.urls),
    path("test_admin/custom_admin/", custom_site.urls),
]
