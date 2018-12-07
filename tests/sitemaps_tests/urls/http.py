from collections import OrderedDict
from datetime import date, datetime

from django.conf.urls.i18n import i18n_patterns
from django.contrib.sitemaps import GenericSitemap, Sitemap, views
from django.http import HttpResponse
from django.urls import path
from django.utils import timezone
from django.views.decorators.cache import cache_page

from ..models import I18nTestModel, TestModel


class SimpleSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5
    location = '/location/'
    lastmod = datetime.now()

    def items(self):
        return [object()]


class SimplePagedSitemap(Sitemap):
    def items(self):
        return [object() for x in range(Sitemap.limit + 1)]


class SimpleI18nSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5
    i18n = True

    def items(self):
        return I18nTestModel.objects.order_by('pk').all()


class EmptySitemap(Sitemap):
    changefreq = "never"
    priority = 0.5
    location = '/location/'


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


class FixedNewerLastmodSitemap(SimpleSitemap):
    lastmod = datetime(2013, 4, 20, 5, 0, 0)


class DateSiteMap(SimpleSitemap):
    lastmod = date(2013, 3, 13)


class TimezoneSiteMap(SimpleSitemap):
    lastmod = datetime(2013, 3, 13, 10, 0, 0, tzinfo=timezone.get_fixed_timezone(-300))


def testmodelview(request, id):
    return HttpResponse()


simple_sitemaps = {
    'simple': SimpleSitemap,
}

simple_i18nsitemaps = {
    'simple': SimpleI18nSitemap,
}

simple_sitemaps_not_callable = {
    'simple': SimpleSitemap(),
}

simple_sitemaps_paged = {
    'simple': SimplePagedSitemap,
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

sitemaps_lastmod_mixed_ascending = OrderedDict([
    ('no-lastmod', EmptySitemap),
    ('lastmod', FixedLastmodSitemap),
])

sitemaps_lastmod_mixed_descending = OrderedDict([
    ('lastmod', FixedLastmodSitemap),
    ('no-lastmod', EmptySitemap),
])

sitemaps_lastmod_ascending = OrderedDict([
    ('date', DateSiteMap),
    ('datetime', FixedLastmodSitemap),
    ('datetime-newer', FixedNewerLastmodSitemap),
])

sitemaps_lastmod_descending = OrderedDict([
    ('datetime-newer', FixedNewerLastmodSitemap),
    ('datetime', FixedLastmodSitemap),
    ('date', DateSiteMap),
])

generic_sitemaps = {
    'generic': GenericSitemap({'queryset': TestModel.objects.order_by('pk').all()}),
}

generic_sitemaps_lastmod = {
    'generic': GenericSitemap({
        'queryset': TestModel.objects.order_by('pk').all(),
        'date_field': 'lastmod',
    }),
}

urlpatterns = [
    path('simple/index.xml', views.index, {'sitemaps': simple_sitemaps}),
    path('simple-paged/index.xml', views.index, {'sitemaps': simple_sitemaps_paged}),
    path('simple-not-callable/index.xml', views.index, {'sitemaps': simple_sitemaps_not_callable}),
    path(
        'simple/custom-index.xml', views.index,
        {'sitemaps': simple_sitemaps, 'template_name': 'custom_sitemap_index.xml'}),
    path(
        'simple/sitemap-<section>.xml', views.sitemap,
        {'sitemaps': simple_sitemaps},
        name='django.contrib.sitemaps.views.sitemap'),
    path(
        'simple/sitemap.xml', views.sitemap,
        {'sitemaps': simple_sitemaps},
        name='django.contrib.sitemaps.views.sitemap'),
    path(
        'simple/i18n.xml', views.sitemap,
        {'sitemaps': simple_i18nsitemaps},
        name='django.contrib.sitemaps.views.sitemap'),
    path(
        'simple/custom-sitemap.xml', views.sitemap,
        {'sitemaps': simple_sitemaps, 'template_name': 'custom_sitemap.xml'},
        name='django.contrib.sitemaps.views.sitemap'),
    path(
        'empty/sitemap.xml', views.sitemap,
        {'sitemaps': empty_sitemaps},
        name='django.contrib.sitemaps.views.sitemap'),
    path(
        'lastmod/sitemap.xml', views.sitemap,
        {'sitemaps': fixed_lastmod_sitemaps},
        name='django.contrib.sitemaps.views.sitemap'),
    path(
        'lastmod-mixed/sitemap.xml', views.sitemap,
        {'sitemaps': fixed_lastmod__mixed_sitemaps},
        name='django.contrib.sitemaps.views.sitemap'),
    path(
        'lastmod/date-sitemap.xml', views.sitemap,
        {'sitemaps': {'date-sitemap': DateSiteMap}},
        name='django.contrib.sitemaps.views.sitemap'),
    path(
        'lastmod/tz-sitemap.xml', views.sitemap,
        {'sitemaps': {'tz-sitemap': TimezoneSiteMap}},
        name='django.contrib.sitemaps.views.sitemap'),
    path(
        'lastmod-sitemaps/mixed-ascending.xml', views.sitemap,
        {'sitemaps': sitemaps_lastmod_mixed_ascending},
        name='django.contrib.sitemaps.views.sitemap'),
    path(
        'lastmod-sitemaps/mixed-descending.xml', views.sitemap,
        {'sitemaps': sitemaps_lastmod_mixed_descending},
        name='django.contrib.sitemaps.views.sitemap'),
    path(
        'lastmod-sitemaps/ascending.xml', views.sitemap,
        {'sitemaps': sitemaps_lastmod_ascending},
        name='django.contrib.sitemaps.views.sitemap'),
    path(
        'lastmod-sitemaps/descending.xml', views.sitemap,
        {'sitemaps': sitemaps_lastmod_descending},
        name='django.contrib.sitemaps.views.sitemap'),
    path(
        'generic/sitemap.xml', views.sitemap,
        {'sitemaps': generic_sitemaps},
        name='django.contrib.sitemaps.views.sitemap'),
    path(
        'generic-lastmod/sitemap.xml', views.sitemap,
        {'sitemaps': generic_sitemaps_lastmod},
        name='django.contrib.sitemaps.views.sitemap'),
    path(
        'cached/index.xml', cache_page(1)(views.index),
        {'sitemaps': simple_sitemaps, 'sitemap_url_name': 'cached_sitemap'}),
    path(
        'cached/sitemap-<section>.xml', cache_page(1)(views.sitemap),
        {'sitemaps': simple_sitemaps}, name='cached_sitemap'),
    path(
        'sitemap-without-entries/sitemap.xml', views.sitemap,
        {'sitemaps': {}}, name='django.contrib.sitemaps.views.sitemap'),
]

urlpatterns += i18n_patterns(
    path('i18n/testmodel/<int:id>/', testmodelview, name='i18n_testmodel'),
)
