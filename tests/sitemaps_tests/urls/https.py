from django.conf.urls import url
from django.contrib.sitemaps import views

from .http import SimpleSitemap


class HTTPSSitemap(SimpleSitemap):
    protocol = 'https'

secure_sitemaps = {
    'simple': HTTPSSitemap,
}

urlpatterns = [
    url(r'^secure/index\.xml$', views.index, {'sitemaps': secure_sitemaps}),
    url(r'^secure/sitemap-(?P<section>.+)\.xml$', views.sitemap,
        {'sitemaps': secure_sitemaps},
        name='django.contrib.sitemaps.views.sitemap'),
]
