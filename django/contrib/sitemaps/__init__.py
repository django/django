from django.contrib.sites.models import Site
from django.core import urlresolvers, paginator
from django.core.exceptions import ImproperlyConfigured
try:
    from urllib.parse import urlencode
    from urllib.request import urlopen
except ImportError:     # Python 2
    from urllib import urlencode, urlopen

PING_URL = "http://www.google.com/webmasters/tools/ping"

class SitemapNotFound(Exception):
    pass

def ping_google(sitemap_url=None, ping_url=PING_URL):
    """
    Alerts Google that the sitemap for the current site has been updated.
    If sitemap_url is provided, it should be an absolute path to the sitemap
    for this site -- e.g., '/sitemap.xml'. If sitemap_url is not provided, this
    function will attempt to deduce it by using urlresolvers.reverse().
    """
    if sitemap_url is None:
        try:
            # First, try to get the "index" sitemap URL.
            sitemap_url = urlresolvers.reverse('django.contrib.sitemaps.views.index')
        except urlresolvers.NoReverseMatch:
            try:
                # Next, try for the "global" sitemap URL.
                sitemap_url = urlresolvers.reverse('django.contrib.sitemaps.views.sitemap')
            except urlresolvers.NoReverseMatch:
                pass

    if sitemap_url is None:
        raise SitemapNotFound("You didn't provide a sitemap_url, and the sitemap URL couldn't be auto-detected.")

    from django.contrib.sites.models import Site
    current_site = Site.objects.get_current()
    url = "http://%s%s" % (current_site.domain, sitemap_url)
    params = urlencode({'sitemap':url})
    urlopen("%s?%s" % (ping_url, params))

class Sitemap(object):
    # This limit is defined by Google. See the index documentation at
    # http://sitemaps.org/protocol.php#index.
    limit = 50000

    # If protocol is None, the URLs in the sitemap will use the protocol
    # with which the sitemap was requested.
    protocol = None

    def __get(self, name, obj, default=None):
        try:
            attr = getattr(self, name)
        except AttributeError:
            return default
        if callable(attr):
            return attr(obj)
        return attr

    def items(self):
        return []

    def location(self, obj):
        return obj.get_absolute_url()

    def _get_paginator(self):
        return paginator.Paginator(self.items(), self.limit)
    paginator = property(_get_paginator)

    def get_urls(self, page=1, site=None, protocol=None):
        # Determine protocol
        if self.protocol is not None:
            protocol = self.protocol
        if protocol is None:
            protocol = 'http'

        # Determine domain
        if site is None:
            if Site._meta.installed:
                try:
                    site = Site.objects.get_current()
                except Site.DoesNotExist:
                    pass
            if site is None:
                raise ImproperlyConfigured("To use sitemaps, either enable the sites framework or pass a Site/RequestSite object in your view.")
        domain = site.domain

        urls = []
        for item in self.paginator.page(page).object_list:
            loc = "%s://%s%s" % (protocol, domain, self.__get('location', item))
            priority = self.__get('priority', item, None)
            url_info = {
                'item':       item,
                'location':   loc,
                'lastmod':    self.__get('lastmod', item, None),
                'changefreq': self.__get('changefreq', item, None),
                'priority':   str(priority if priority is not None else ''),
            }
            urls.append(url_info)
        return urls

class FlatPageSitemap(Sitemap):
    def items(self):
        current_site = Site.objects.get_current()
        return current_site.flatpage_set.filter(registration_required=False)

class GenericSitemap(Sitemap):
    priority = None
    changefreq = None

    def __init__(self, info_dict, priority=None, changefreq=None):
        self.queryset = info_dict['queryset']
        self.date_field = info_dict.get('date_field', None)
        self.priority = priority
        self.changefreq = changefreq

    def items(self):
        # Make sure to return a clone; we don't want premature evaluation.
        return self.queryset.filter()

    def lastmod(self, item):
        if self.date_field is not None:
            return getattr(item, self.date_field)
        return None
