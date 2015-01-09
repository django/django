from django.conf.urls import patterns, url
from django.contrib.auth import views


urlpatterns = patterns('',
    url(r'^accounts/logout/$', views.logout, name='logout'),
)
