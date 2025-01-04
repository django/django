from django.urls import path

from .models import site_gis

urlpatterns = [
    path("admin/", site_gis.urls),
]
