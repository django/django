from django.urls import path

from .admin import admin

urlpatterns = [
    path("admin/", admin.site.urls),
]
