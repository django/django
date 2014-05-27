from __future__ import unicode_literals

from freedom.conf.urls import url
from freedom.contrib.gis import views as gis_views
from freedom.contrib.sitemaps import views as sitemap_views
from freedom.contrib.gis.sitemaps import views as gis_sitemap_views

from .feeds import feed_dict
from .sitemaps import sitemaps


urlpatterns = [
    url(r'^feeds/(?P<url>.*)/$', gis_views.feed, {'feed_dict': feed_dict}),
]

urlpatterns += [
    url(r'^sitemaps/(?P<section>\w+)\.xml$', sitemap_views.sitemap, {'sitemaps': sitemaps}),
]

urlpatterns += [
    url(r'^sitemaps/kml/(?P<label>\w+)/(?P<model>\w+)/(?P<field_name>\w+)\.kml$', gis_sitemap_views.kml),
    url(r'^sitemaps/kml/(?P<label>\w+)/(?P<model>\w+)/(?P<field_name>\w+)\.kmz$', gis_sitemap_views.kmz),
]
