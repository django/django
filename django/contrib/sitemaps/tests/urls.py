from datetime import datetime
from django.conf.urls.defaults import *
from django.contrib.sitemaps import Sitemap

class SimpleSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5
    location = '/ticket14164'
    lastmod = datetime.now()

    def items(self):
        return [object()]

sitemaps = {
    'simple': SimpleSitemap,
}

urlpatterns = patterns('django.contrib.sitemaps.views',
    (r'^sitemaps/sitemap\.xml$', 'sitemap', {'sitemaps': sitemaps}),
)
