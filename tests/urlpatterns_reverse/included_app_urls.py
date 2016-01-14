from django.conf.urls import url

from . import views

app_name = 'inc-app'
urlpatterns = [
    url(r'^normal/$', views.empty_view, name='inc-normal-view'),
    url(r'^normal/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', views.empty_view, name='inc-normal-view'),

    url(r'^\+\\\$\*/$', views.empty_view, name='inc-special-view'),

    url(r'^mixed_args/([0-9]+)/(?P<arg2>[0-9]+)/$', views.empty_view, name='inc-mixed-args'),
    url(r'^no_kwargs/([0-9]+)/([0-9]+)/$', views.empty_view, name='inc-no-kwargs'),

    url(r'^view_class/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', views.view_class_instance, name='inc-view-class'),
]
