from thibaud.contrib import admin
from thibaud.urls import include, path

urlpatterns = [
    path("admin/", include(admin.site.urls)),
]
