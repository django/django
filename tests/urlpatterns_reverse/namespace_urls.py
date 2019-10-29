from django.urls import include, path, re_path

from . import views
from .utils import URLObject

testobj1 = URLObject('testapp', 'test-ns1')
testobj2 = URLObject('testapp', 'test-ns2')
default_testobj = URLObject('testapp', 'testapp')

otherobj1 = URLObject('nodefault', 'other-ns1')
otherobj2 = URLObject('nodefault', 'other-ns2')

newappobj1 = URLObject('newapp')

app_name = 'namespace_urls'
urlpatterns = [
    path('normal/', views.empty_view, name='normal-view'),
    re_path(r'^normal/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', views.empty_view, name='normal-view'),
    path('resolver_match/', views.pass_resolver_match_view, name='test-resolver-match'),

    re_path(r'^\+\\\$\*/$', views.empty_view, name='special-view'),

    re_path(r'^mixed_args/([0-9]+)/(?P<arg2>[0-9]+)/$', views.empty_view, name='mixed-args'),
    re_path(r'^no_kwargs/([0-9]+)/([0-9]+)/$', views.empty_view, name='no-kwargs'),

    re_path(r'^view_class/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', views.view_class_instance, name='view-class'),

    re_path(r'^unnamed/normal/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', views.empty_view),
    re_path(r'^unnamed/view_class/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', views.view_class_instance),

    path('test1/', include(*testobj1.urls)),
    path('test2/', include(*testobj2.urls)),
    path('default/', include(*default_testobj.urls)),

    path('other1/', include(*otherobj1.urls)),
    re_path(r'^other[246]/', include(*otherobj2.urls)),

    path('newapp1/', include(newappobj1.app_urls, 'new-ns1')),
    path('new-default/', include(newappobj1.app_urls)),

    re_path(r'^app-included[135]/', include('urlpatterns_reverse.included_app_urls', namespace='app-ns1')),
    path('app-included2/', include('urlpatterns_reverse.included_app_urls', namespace='app-ns2')),

    re_path(r'^ns-included[135]/', include('urlpatterns_reverse.included_namespace_urls', namespace='inc-ns1')),
    path('ns-included2/', include('urlpatterns_reverse.included_namespace_urls', namespace='inc-ns2')),

    path('app-included/', include('urlpatterns_reverse.included_namespace_urls', 'inc-app')),

    path('included/', include('urlpatterns_reverse.included_namespace_urls')),
    re_path(
        r'^inc(?P<outer>[0-9]+)/', include(('urlpatterns_reverse.included_urls', 'included_urls'), namespace='inc-ns5')
    ),
    re_path(r'^included/([0-9]+)/', include('urlpatterns_reverse.included_namespace_urls')),

    re_path(
        r'^ns-outer/(?P<outer>[0-9]+)/',
        include('urlpatterns_reverse.included_namespace_urls', namespace='inc-outer')
    ),

    re_path(r'^\+\\\$\*/', include('urlpatterns_reverse.namespace_urls', namespace='special')),
]
