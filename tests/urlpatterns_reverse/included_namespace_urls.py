from __future__ import absolute_import

from django.conf.urls import patterns, url, include

from .namespace_urls import URLObject
from .views import view_class_instance


testobj3 = URLObject('testapp', 'test-ns3')

urlpatterns = patterns('urlpatterns_reverse.views',
    url(r'^normal/$', 'empty_view', name='inc-normal-view'),
    url(r'^normal/(?P<arg1>\d+)/(?P<arg2>\d+)/$', 'empty_view', name='inc-normal-view'),

    url(r'^\+\\\$\*/$', 'empty_view', name='inc-special-view'),

    url(r'^mixed_args/(\d+)/(?P<arg2>\d+)/$', 'empty_view', name='inc-mixed-args'),
    url(r'^no_kwargs/(\d+)/(\d+)/$', 'empty_view', name='inc-no-kwargs'),

    url(r'^view_class/(?P<arg1>\d+)/(?P<arg2>\d+)/$', view_class_instance, name='inc-view-class'),

    (r'^test3/', include(testobj3.urls)),
    (r'^ns-included3/', include('urlpatterns_reverse.included_urls', namespace='inc-ns3')),
    (r'^ns-included4/', include('urlpatterns_reverse.namespace_urls', namespace='inc-ns4')),
)

