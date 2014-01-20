from django.conf.urls import patterns, include, url

from django.contrib import admin

urlpatterns = patterns('',
    # This is the same as in the default project template
    url(r'^admin/', include(admin.site.urls)),
)
