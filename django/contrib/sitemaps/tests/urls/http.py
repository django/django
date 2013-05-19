from datetime import datetime
from django.conf.urls import patterns, url
from django.contrib.sitemaps import Sitemap, GenericSitemap, FlatPageSitemap, views
from django.contrib.auth.models import User
from django.views.decorators.cache import cache_page

from django.contrib.sitemaps.tests.base import TestModel


class SimpleSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5
    location = '/location/'
    lastmod = datetime.now()

    def items(self):
        return [object()]

simple_sitemaps = {
    'simple': SimpleSitemap,
}

generic_sitemaps = {
    'generic': GenericSitemap({'queryset': TestModel.objects.all()}),
}

flatpage_sitemaps = {
    'flatpages': FlatPageSitemap,
}

urlpatterns = patterns('django.contrib.sitemaps.views',
    (r'^simple/index\.xml$', 'index', {'sitemaps': simple_sitemaps}),
    (r'^simple/custom-index\.xml$', 'index',
        {'sitemaps': simple_sitemaps, 'template_name': 'custom_sitemap_index.xml'}),
    (r'^simple/sitemap-(?P<section>.+)\.xml$', 'sitemap',
        {'sitemaps': simple_sitemaps}),
    (r'^simple/sitemap\.xml$', 'sitemap', {'sitemaps': simple_sitemaps}),
    (r'^simple/custom-sitemap\.xml$', 'sitemap',
        {'sitemaps': simple_sitemaps, 'template_name': 'custom_sitemap.xml'}),
    (r'^generic/sitemap\.xml$', 'sitemap', {'sitemaps': generic_sitemaps}),
    (r'^flatpages/sitemap\.xml$', 'sitemap', {'sitemaps': flatpage_sitemaps}),
    url(r'^cached/index\.xml$', cache_page(1)(views.index),
        {'sitemaps': simple_sitemaps, 'sitemap_url_name': 'cached_sitemap'}),
    url(r'^cached/sitemap-(?P<section>.+)\.xml', cache_page(1)(views.sitemap),
        {'sitemaps': simple_sitemaps}, name='cached_sitemap')
)
