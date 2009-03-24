from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    ('^$', views.index),
    ('^last_modified/$', views.last_modified_view1),
    ('^last_modified2/$', views.last_modified_view2),
    ('^etag/$', views.etag_view1),
    ('^etag2/$', views.etag_view2),
)
