from django.conf.urls.defaults import *
import views

urlpatterns = patterns('',
    ('^$', views.index),
    ('^last_modified/$', views.last_modified),
    ('^etag/$', views.etag),
)
