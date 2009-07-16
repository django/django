from django.conf.urls.defaults import *

class URLObject(object):
    def __init__(self, app_name, namespace):
        self.app_name = app_name
        self.namespace = namespace

    def urls(self):
        return patterns('',
            url(r'^inner/$', 'empty_view', name='urlobject-view'),
            url(r'^inner/(?P<arg1>\d+)/(?P<arg2>\d+)/$', 'empty_view', name='urlobject-view'),
        ), self.app_name, self.namespace
    urls = property(urls)

testobj1 = URLObject('testapp', 'test-ns1')
testobj2 = URLObject('testapp', 'test-ns2')
default_testobj = URLObject('testapp', 'testapp')

otherobj1 = URLObject('nodefault', 'other-ns1')
otherobj2 = URLObject('nodefault', 'other-ns2')

urlpatterns = patterns('regressiontests.urlpatterns_reverse.views',
    url(r'^normal/$', 'empty_view', name='normal-view'),
    url(r'^normal/(?P<arg1>\d+)/(?P<arg2>\d+)/$', 'empty_view', name='normal-view'),

    (r'^test1/', include(testobj1.urls)),
    (r'^test2/', include(testobj2.urls)),
    (r'^default/', include(default_testobj.urls)),

    (r'^other1/', include(otherobj1.urls)),
    (r'^other2/', include(otherobj2.urls)),

    (r'^ns-included1/', include('regressiontests.urlpatterns_reverse.included_namespace_urls', namespace='inc-ns1')),
    (r'^ns-included2/', include('regressiontests.urlpatterns_reverse.included_namespace_urls', namespace='inc-ns2')),

    (r'^included/', include('regressiontests.urlpatterns_reverse.included_namespace_urls')),

)
