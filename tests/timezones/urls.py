from django.conf.urls import include, url

from . import admin as tz_admin  # NOQA: register tz_admin

urlpatterns = [
    url(r'^admin/', include(tz_admin.site.urls)),
]
