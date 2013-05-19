from __future__ import absolute_import

from django.conf.urls import patterns, include

from . import admin

urlpatterns = patterns('',
    (r'^generic_inline_admin/admin/', include(admin.site.urls)),
)
