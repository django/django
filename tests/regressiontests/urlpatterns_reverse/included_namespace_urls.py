from django.conf.urls.defaults import *
from namespace_urls import URLObject

testobj3 = URLObject('testapp', 'test-ns3')

urlpatterns = patterns('regressiontests.urlpatterns_reverse.views',
    url(r'^normal/$', 'empty_view', name='inc-normal-view'),
    url(r'^normal/(?P<arg1>\d+)/(?P<arg2>\d+)/$', 'empty_view', name='inc-normal-view'),

    url(r'^mixed_args/(\d+)/(?P<arg2>\d+)/$', 'empty_view', name='inc-mixed-args'),
    url(r'^no_kwargs/(\d+)/(\d+)/$', 'empty_view', name='inc-no-kwargs'),

    (r'^test3/', include(testobj3.urls)),
    (r'^ns-included3/', include('regressiontests.urlpatterns_reverse.included_urls', namespace='inc-ns3')),
    (r'^ns-included4/', include('regressiontests.urlpatterns_reverse.namespace_urls', namespace='inc-ns4')),
)

