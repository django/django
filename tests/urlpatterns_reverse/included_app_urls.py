from django.urls import path, re_path

from . import views

app_name = 'inc-app'
urlpatterns = [
    path('normal/', views.empty_view, name='inc-normal-view'),
    re_path('^normal/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', views.empty_view, name='inc-normal-view'),

    re_path(r'^\+\\\$\*/$', views.empty_view, name='inc-special-view'),

    re_path('^mixed_args/([0-9]+)/(?P<arg2>[0-9]+)/$', views.empty_view, name='inc-mixed-args'),
    re_path('^no_kwargs/([0-9]+)/([0-9]+)/$', views.empty_view, name='inc-no-kwargs'),

    re_path('^view_class/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', views.view_class_instance, name='inc-view-class'),
]
