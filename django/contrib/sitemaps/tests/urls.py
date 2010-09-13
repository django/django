from datetime import datetime
from django.conf.urls.defaults import *
from django.contrib.sitemaps import Sitemap, GenericSitemap, FlatPageSitemap
from django.contrib.auth.models import User

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
    'generic': GenericSitemap({
        'queryset': User.objects.all()
    }),
}

flatpage_sitemaps = {
    'flatpages': FlatPageSitemap,
}

urlpatterns = patterns('django.contrib.sitemaps.views',
    (r'^simple/sitemap\.xml$', 'sitemap', {'sitemaps': simple_sitemaps}),
    (r'^generic/sitemap\.xml$', 'sitemap', {'sitemaps': generic_sitemaps}),
    (r'^flatpages/sitemap\.xml$', 'sitemap', {'sitemaps': flatpage_sitemaps}),
)
