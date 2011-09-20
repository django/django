from django.conf.urls import patterns, include

import admin

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
)
