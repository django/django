from django.conf.urls import patterns, include
from django.contrib import admin

from . import admin as tz_admin  # NOQA: register tz_admin

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
)
