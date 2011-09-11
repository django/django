from django.conf.urls import patterns, include
import widgetadmin

urlpatterns = patterns('',
    (r'^', include(widgetadmin.site.urls)),
)
