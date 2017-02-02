from django.conf.urls import url
from django.contrib.sitemaps import views

from .http import simple_sitemaps

urlpatterns = [
    url(r'^simple/index\.xml$', views.index, {'sitemaps': simple_sitemaps},
        name='django.contrib.sitemaps.views.index'),
]
