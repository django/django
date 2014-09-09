from datetime import date, datetime
from django.conf.urls import patterns, url
from django.contrib.sitemaps import Sitemap, GenericSitemap, FlatPageSitemap, views
from django.utils import timezone
from django.views.decorators.cache import cache_page

from django.contrib.sitemaps.tests.base import TestModel


class SimpleSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5
    location = '/location/'
    lastmod = datetime.now()

    def items(self):
        return [object()]


class EmptySitemap(Sitemap):
    changefreq = "never"
    priority = 0.5
    location = '/location/'

    def items(self):
        return []


class FixedLastmodSitemap(SimpleSitemap):
    lastmod = datetime(2013, 3, 13, 10, 0, 0)


class FixedLastmodMixedSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5
    location = '/location/'
    loop = 0

    def items(self):
        o1 = TestModel()
        o1.lastmod = datetime(2013, 3, 13, 10, 0, 0)
        o2 = TestModel()
        return [o1, o2]


class DateSiteMap(SimpleSitemap):
    lastmod = date(2013, 3, 13)


class TimezoneSiteMap(SimpleSitemap):
    lastmod = datetime(2013, 3, 13, 10, 0, 0, tzinfo=timezone.get_fixed_timezone(-300))


simple_sitemaps = {
    'simple': SimpleSitemap,
}

empty_sitemaps = {
    'empty': EmptySitemap,
}

fixed_lastmod_sitemaps = {
    'fixed-lastmod': FixedLastmodSitemap,
}

fixed_lastmod__mixed_sitemaps = {
    'fixed-lastmod-mixed': FixedLastmodMixedSitemap,
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
    (r'^empty/sitemap\.xml$', 'sitemap', {'sitemaps': empty_sitemaps}),
    (r'^lastmod/sitemap\.xml$', 'sitemap', {'sitemaps': fixed_lastmod_sitemaps}),
    (r'^lastmod-mixed/sitemap\.xml$', 'sitemap', {'sitemaps': fixed_lastmod__mixed_sitemaps}),
    url(r'^lastmod/date-sitemap.xml$', views.sitemap,
        {'sitemaps': {'date-sitemap': DateSiteMap}}),
    url(r'^lastmod/tz-sitemap.xml$', views.sitemap,
        {'sitemaps': {'tz-sitemap': TimezoneSiteMap}}),
    (r'^generic/sitemap\.xml$', 'sitemap', {'sitemaps': generic_sitemaps}),
    (r'^flatpages/sitemap\.xml$', 'sitemap', {'sitemaps': flatpage_sitemaps}),
    url(r'^cached/index\.xml$', cache_page(1)(views.index),
        {'sitemaps': simple_sitemaps, 'sitemap_url_name': 'cached_sitemap'}),
    url(r'^cached/sitemap-(?P<section>.+)\.xml', cache_page(1)(views.sitemap),
        {'sitemaps': simple_sitemaps}, name='cached_sitemap')
)
