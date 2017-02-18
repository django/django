from django.conf.urls import include, url

from . import admin

urlpatterns = [
    url(r'^generic_inline_admin/admin/', include(admin.site.urls)),
]
