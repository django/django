from django.conf.urls import include, url

from . import views


class URLObject(object):
    def __init__(self, app_name, namespace):
        self.app_name = app_name
        self.namespace = namespace

    def urls(self):
        return ([
            url(r'^inner/$', views.empty_view, name='urlobject-view'),
            url(r'^inner/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', views.empty_view, name='urlobject-view'),
            url(r'^inner/\+\\\$\*/$', views.empty_view, name='urlobject-special-view'),
        ], self.app_name, self.namespace)
    urls = property(urls)

testobj1 = URLObject('testapp', 'test-ns1')
testobj2 = URLObject('testapp', 'test-ns2')
default_testobj = URLObject('testapp', 'testapp')

otherobj1 = URLObject('nodefault', 'other-ns1')
otherobj2 = URLObject('nodefault', 'other-ns2')

urlpatterns = [
    url(r'^normal/$', views.empty_view, name='normal-view'),
    url(r'^normal/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', views.empty_view, name='normal-view'),
    url(r'^resolver_match/$', views.pass_resolver_match_view, name='test-resolver-match'),

    url(r'^\+\\\$\*/$', views.empty_view, name='special-view'),

    url(r'^mixed_args/([0-9]+)/(?P<arg2>[0-9]+)/$', views.empty_view, name='mixed-args'),
    url(r'^no_kwargs/([0-9]+)/([0-9]+)/$', views.empty_view, name='no-kwargs'),

    url(r'^view_class/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', views.view_class_instance, name='view-class'),

    url(r'^unnamed/normal/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', views.empty_view),
    url(r'^unnamed/view_class/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', views.view_class_instance),

    url(r'^test1/', include(testobj1.urls)),
    url(r'^test2/', include(testobj2.urls)),
    url(r'^default/', include(default_testobj.urls)),

    url(r'^other1/', include(otherobj1.urls)),
    url(r'^other[246]/', include(otherobj2.urls)),

    url(r'^ns-included[135]/', include('urlpatterns_reverse.included_namespace_urls', namespace='inc-ns1')),
    url(r'^ns-included2/', include('urlpatterns_reverse.included_namespace_urls', namespace='inc-ns2')),

    url(r'^included/', include('urlpatterns_reverse.included_namespace_urls')),
    url(r'^inc(?P<outer>[0-9]+)/', include('urlpatterns_reverse.included_urls', namespace='inc-ns5')),

    url(r'^ns-outer/(?P<outer>[0-9]+)/', include('urlpatterns_reverse.included_namespace_urls', namespace='inc-outer')),

    url(r'^\+\\\$\*/', include('urlpatterns_reverse.namespace_urls', namespace='special')),
]
