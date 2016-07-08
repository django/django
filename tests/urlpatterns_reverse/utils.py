from __future__ import unicode_literals

from django.conf.urls import url

from . import views


class URLObject(object):
    urlpatterns = [
        url(r'^inner/$', views.empty_view, name='urlobject-view'),
        url(r'^inner/(?P<arg1>[0-9]+)/(?P<arg2>[0-9]+)/$', views.empty_view, name='urlobject-view'),
        url(r'^inner/\+\\\$\*/$', views.empty_view, name='urlobject-special-view'),
    ]

    def __init__(self, app_name, namespace=None):
        self.app_name = app_name
        self.namespace = namespace

    @property
    def urls(self):
        return self.urlpatterns, self.app_name, self.namespace

    @property
    def app_urls(self):
        return self.urlpatterns, self.app_name
