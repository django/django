from __future__ import unicode_literals

from django.conf.urls import include, url

from . import admin

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
]
