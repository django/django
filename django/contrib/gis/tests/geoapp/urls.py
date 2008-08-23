from django.conf.urls.defaults import *
from feeds import feed_dict

urlpatterns = patterns('',
    (r'^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.feed', {'feed_dict': feed_dict}),
)

from sitemaps import sitemaps
urlpatterns += patterns('django.contrib.gis.sitemaps.views',
    (r'^sitemap.xml$', 'index', {'sitemaps' : sitemaps}),
    (r'^sitemaps/(?P<section>\w+)\.xml$', 'sitemap', {'sitemaps' : sitemaps}),
    (r'^sitemaps/kml/(?P<label>\w+)/(?P<model>\w+)/(?P<field_name>\w+)\.kml$', 'kml'),
    (r'^sitemaps/kml/(?P<label>\w+)/(?P<model>\w+)/(?P<field_name>\w+)\.kmz$', 'kmz'),                
)
