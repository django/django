from __future__ import absolute_import

from django.conf.urls import patterns, url, include

from .views import namespaced_view_class_instance

deeper_patterns = patterns('',
    (r'^view_class/$', namespaced_view_class_instance),
)

urlpatterns = patterns('regressiontests.urlpatterns_reverse.views',
    url(r'^deeper/', include(deeper_patterns)),
)

