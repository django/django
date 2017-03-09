from contextlib import suppress
from urllib.parse import urlencode
from urllib.request import urlopen

from django.apps import apps as django_apps
from django.conf import settings
from django.core import paginator
from django.core.exceptions import ImproperlyConfigured
from django.urls import NoReverseMatch, reverse
from django.utils import translation

PING_URL = "https://www.google.com/webmasters/tools/ping"


class SitemapNotFound(Exception):
    pass


def ping_google(sitemap_url=None, ping_url=PING_URL):
    """
    Alert Google that the sitemap for the current site has been updated.
    If sitemap_url is provided, it should be an absolute path to the sitemap
    for this site -- e.g., '/sitemap.xml'. If sitemap_url is not provided, this
    function will attempt to deduce it by using urls.reverse().
    """
    sitemap_full_url = _get_sitemap_full_url(sitemap_url)
    params = urlencode({'sitemap': sitemap_full_url})
    urlopen('%s?%s' % (ping_url, params))


def _get_sitemap_full_url(sitemap_url):
    if not django_apps.is_installed('django.contrib.sites'):
        raise ImproperlyConfigured("ping_google requires django.contrib.sites, which isn't installed.")

    if sitemap_url is None:
        try:
            # First, try to get the "index" sitemap URL.
            sitemap_url = reverse('django.contrib.sitemaps.views.index')
        except NoReverseMatch:
            with suppress(NoReverseMatch):
                # Next, try for the "global" sitemap URL.
                sitemap_url = reverse('django.contrib.sitemaps.views.sitemap')

    if sitemap_url is None:
        raise SitemapNotFound("You didn't provide a sitemap_url, and the sitemap URL couldn't be auto-detected.")

    Site = django_apps.get_model('sites.Site')
    current_site = Site.objects.get_current()
    return 'http://%s%s' % (current_site.domain, sitemap_url)


class Sitemap:
    # This limit is defined by Google. See the index documentation at
    # http://www.sitemaps.org/protocol.html#index.
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

    @property
    def paginator(self):
        return paginator.Paginator(self.items(), self.limit)

    def get_urls(self, page=1, site=None, protocol=None):
        # Determine protocol
        if self.protocol is not None:
            protocol = self.protocol
        if protocol is None:
            protocol = 'http'

        # Determine domain
        if site is None:
            if django_apps.is_installed('django.contrib.sites'):
                Site = django_apps.get_model('sites.Site')
                with suppress(Site.DoesNotExist):
                    site = Site.objects.get_current()
            if site is None:
                raise ImproperlyConfigured(
                    "To use sitemaps, either enable the sites framework or pass "
                    "a Site/RequestSite object in your view."
                )
        domain = site.domain

        if getattr(self, 'i18n', False):
            urls = []
            current_lang_code = translation.get_language()
            for lang_code, lang_name in settings.LANGUAGES:
                translation.activate(lang_code)
                urls += self._urls(page, protocol, domain)
            translation.activate(current_lang_code)
        else:
            urls = self._urls(page, protocol, domain)

        return urls

    def _urls(self, page, protocol, domain):
        urls = []
        latest_lastmod = None
        all_items_lastmod = True  # track if all items have a lastmod
        for item in self.paginator.page(page).object_list:
            loc = "%s://%s%s" % (protocol, domain, self.__get('location', item))
            priority = self.__get('priority', item)
            lastmod = self.__get('lastmod', item)
            if all_items_lastmod:
                all_items_lastmod = lastmod is not None
                if (all_items_lastmod and
                        (latest_lastmod is None or lastmod > latest_lastmod)):
                    latest_lastmod = lastmod
            url_info = {
                'item': item,
                'location': loc,
                'lastmod': lastmod,
                'changefreq': self.__get('changefreq', item),
                'priority': str(priority if priority is not None else ''),
            }
            urls.append(url_info)
        if all_items_lastmod and latest_lastmod:
            self.latest_lastmod = latest_lastmod
        return urls


class GenericSitemap(Sitemap):
    priority = None
    changefreq = None

    def __init__(self, info_dict, priority=None, changefreq=None, protocol=None):
        self.queryset = info_dict['queryset']
        self.date_field = info_dict.get('date_field')
        self.priority = priority
        self.changefreq = changefreq
        self.protocol = protocol

    def items(self):
        # Make sure to return a clone; we don't want premature evaluation.
        return self.queryset.filter()

    def lastmod(self, item):
        if self.date_field is not None:
            return getattr(item, self.date_field)
        return None


default_app_config = 'django.contrib.sitemaps.apps.SiteMapsConfig'
