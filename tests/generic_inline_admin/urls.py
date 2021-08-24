from django.urls import path

from . import admin

urlpatterns = [
    path("generic_inline_admin/admin/", admin.site.urls),
]
