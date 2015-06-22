import warnings

from django.conf.urls import include, patterns, url
from django.utils.deprecation import RemovedInDjango110Warning

from .namespace_urls import URLObject
from .views import view_class_instance

testobj3 = URLObject('testapp', 'test-ns3')

# test deprecated patterns() function. convert to list of urls() in Django 1.10
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', category=RemovedInDjango110Warning)

    urlpatterns = patterns('urlpatterns_reverse.views',
        url(r'^normal/$', 'empty_view', name='inc-normal-view'),
        url(r'^normal/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', 'empty_view', name='inc-normal-view'),

        url(r'^\+\\\$\*/$', 'empty_view', name='inc-special-view'),

        url(r'^mixed_args/([0-9]+)/(?P<arg2>[0-9]+)/$', 'empty_view', name='inc-mixed-args'),
        url(r'^no_kwargs/([0-9]+)/([0-9]+)/$', 'empty_view', name='inc-no-kwargs'),

        url(r'^view_class/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', view_class_instance, name='inc-view-class'),

        (r'^test3/', include(testobj3.urls)),
        (r'^ns-included3/', include('urlpatterns_reverse.included_urls', namespace='inc-ns3')),
        (r'^ns-included4/', include('urlpatterns_reverse.namespace_urls', namespace='inc-ns4')),
    )
