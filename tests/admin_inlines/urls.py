from django.urls import path

from . import admin

urlpatterns = [
    path("admin/", admin.site.urls),
    path("admin2/", admin.site2.urls),
    path("admin3/", admin.site3.urls),
    path("admin4/", admin.site4.urls),
]
