from django.conf.urls import patterns, include

from . import widgetadmin


urlpatterns = patterns('',
    (r'^', include(widgetadmin.site.urls)),
    (r'^my_admin_url/', include(widgetadmin.my_admin_site.urls)),
)
