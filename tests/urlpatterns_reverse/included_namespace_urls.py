from django.conf.urls import include, url

from .utils import URLObject
from .views import empty_view, view_class_instance

testobj3 = URLObject('testapp', 'test-ns3')
testobj4 = URLObject('testapp', 'test-ns4')

urlpatterns = [
    url(r'^normal/$', empty_view, name='inc-normal-view'),
    url(r'^normal/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', empty_view, name='inc-normal-view'),

    url(r'^\+\\\$\*/$', empty_view, name='inc-special-view'),

    url(r'^mixed_args/([0-9]+)/(?P<arg2>[0-9]+)/$', empty_view, name='inc-mixed-args'),
    url(r'^no_kwargs/([0-9]+)/([0-9]+)/$', empty_view, name='inc-no-kwargs'),

    url(r'^view_class/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', view_class_instance, name='inc-view-class'),

    url(r'^test3/', include(testobj3.urls)),
    url(r'^test4/', include(testobj4.urls)),
    url(r'^ns-included3/', include('urlpatterns_reverse.included_urls', namespace='inc-ns3')),
    url(r'^ns-included4/', include('urlpatterns_reverse.namespace_urls', namespace='inc-ns4')),
]
