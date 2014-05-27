from freedom.conf.urls import include, url
from freedom.contrib import admin

from . import admin as tz_admin  # NOQA: register tz_admin

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
]
