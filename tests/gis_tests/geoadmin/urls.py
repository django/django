from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", include(admin.site.urls)),
]
