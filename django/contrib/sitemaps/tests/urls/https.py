from django.conf.urls import patterns

from .http import SimpleSitemap

class HTTPSSitemap(SimpleSitemap):
    protocol = 'https'

secure_sitemaps = {
    'simple': HTTPSSitemap,
}

urlpatterns = patterns('django.contrib.sitemaps.views',
    (r'^secure/index\.xml$', 'index', {'sitemaps': secure_sitemaps}),
    (r'^secure/sitemap-(?P<section>.+)\.xml$', 'sitemap',
        {'sitemaps': secure_sitemaps}),
)
