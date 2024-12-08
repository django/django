from django.urls import path

from .admin import custom_site, site

urlpatterns = [
    path("test_admin/admin/", site.urls),
    path("test_admin/custom_admin/", custom_site.urls),
]
