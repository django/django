from django.urls import path

from . import admin as tz_admin  # NOQA: register tz_admin

urlpatterns = [
    path("admin/", tz_admin.site.urls),
]
