from __future__ import absolute_import

from django.conf.urls import patterns, include
from django.contrib import admin

from . import admin as tz_admin

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
)
