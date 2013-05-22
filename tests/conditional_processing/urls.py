from django.conf.urls import patterns

from . import views


urlpatterns = patterns('',
    ('^condition/$', views.index),
    ('^condition/last_modified/$', views.last_modified_view1),
    ('^condition/last_modified2/$', views.last_modified_view2),
    ('^condition/etag/$', views.etag_view1),
    ('^condition/etag2/$', views.etag_view2),
)
