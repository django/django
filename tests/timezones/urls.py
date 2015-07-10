from django.conf.urls import url

from . import admin as tz_admin  # NOQA: register tz_admin

urlpatterns = [
    url(r'^admin/', tz_admin.site.urls),
]
