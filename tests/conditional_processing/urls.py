from django.conf.urls import url

from . import views

urlpatterns = [
    url('^condition/$', views.index),
    url('^condition/last_modified/$', views.last_modified_view1),
    url('^condition/last_modified2/$', views.last_modified_view2),
    url('^condition/etag/$', views.etag_view1),
    url('^condition/etag2/$', views.etag_view2),
    url('^condition/unquoted_etag/$', views.etag_view_unquoted),
    url('^condition/weak_etag/$', views.etag_view_weak),
    url('^condition/no_etag/$', views.etag_view_none),
]
