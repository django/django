import warnings
from urllib.parse import urlencode
from urllib.request import urlopen

from django.apps import apps as django_apps
from django.conf import settings
from django.core import paginator
from django.core.exceptions import ImproperlyConfigured
from django.urls import NoReverseMatch, reverse
from django.utils import translation
from django.utils.deprecation import RemovedInDjango50Warning

PING_URL = "https://www.google.com/webmasters/tools/ping"


class SitemapNotFound(Exception):
    pass


def ping_google(sitemap_url=None, ping_url=PING_URL, sitemap_uses_https=True):
    """
    Alert Google that the sitemap for the current site has been updated.
    If sitemap_url is provided, it should be an absolute path to the sitemap
    for this site -- e.g., '/sitemap.xml'. If sitemap_url is not provided, this
    function will attempt to deduce it by using urls.reverse().
    """
    sitemap_full_url = _get_sitemap_full_url(sitemap_url, sitemap_uses_https)
    params = urlencode({"sitemap": sitemap_full_url})
    urlopen("%s?%s" % (ping_url, params))


def _get_sitemap_full_url(sitemap_url, sitemap_uses_https=True):
    if not django_apps.is_installed("django.contrib.sites"):
        raise ImproperlyConfigured(
            "ping_google requires django.contrib.sites, which isn't installed."
        )

    if sitemap_url is None:
        try:
            # First, try to get the "index" sitemap URL.
            sitemap_url = reverse("django.contrib.sitemaps.views.index")
        except NoReverseMatch:
            try:
                # Next, try for the "global" sitemap URL.
                sitemap_url = reverse("django.contrib.sitemaps.views.sitemap")
            except NoReverseMatch:
                pass

    if sitemap_url is None:
        raise SitemapNotFound(
            "You didn't provide a sitemap_url, and the sitemap URL couldn't be "
            "auto-detected."
        )

    Site = django_apps.get_model("sites.Site")
    current_site = Site.objects.get_current()
    scheme = "https" if sitemap_uses_https else "http"
    return "%s://%s%s" % (scheme, current_site.domain, sitemap_url)


class Sitemap:
    # This limit is defined by Google. See the index documentation at
    # https://www.sitemaps.org/protocol.html#index.
    limit = 50000

    # If protocol is None, the URLs in the sitemap will use the protocol
    # with which the sitemap was requested.
    protocol = None

    # Enables generating URLs for all languages.
    i18n = False

    # Override list of languages to use.
    languages = None

    # Enables generating alternate/hreflang links.
    alternates = False

    # Add an alternate/hreflang link with value 'x-default'.
    x_default = False

    def _get(self, name, item, default=None):
        try:
            attr = getattr(self, name)
        except AttributeError:
            return default
        if callable(attr):
            if self.i18n:
                # Split the (item, lang_code) tuples again for the location,
                # priority, lastmod and changefreq method calls.
                item, lang_code = item
            return attr(item)
        return attr

    def _languages(self):
        if self.languages is not None:
            return self.languages
        return [lang_code for lang_code, _ in settings.LANGUAGES]

    def _items(self):
        if self.i18n:
            # Create (item, lang_code) tuples for all items and languages.
            # This is necessary to paginate with all languages already considered.
            items = [
                (item, lang_code)
                for lang_code in self._languages()
                for item in self.items()
            ]
            return items
        return self.items()

    def _location(self, item, force_lang_code=None):
        if self.i18n:
            obj, lang_code = item
            # Activate language from item-tuple or forced one before calling location.
            with translation.override(force_lang_code or lang_code):
                return self._get("location", item)
        return self._get("location", item)

    @property
    def paginator(self):
        return paginator.Paginator(self._items(), self.limit)

    def items(self):
        return []

    def location(self, item):
        return item.get_absolute_url()

    def get_protocol(self, protocol=None):
        # Determine protocol
        if self.protocol is None and protocol is None:
            warnings.warn(
                "The default sitemap protocol will be changed from 'http' to "
                "'https' in Django 5.0. Set Sitemap.protocol to silence this "
                "warning.",
                category=RemovedInDjango50Warning,
                stacklevel=2,
            )
        # RemovedInDjango50Warning: when the deprecation ends, replace 'http'
        # with 'https'.
        return self.protocol or protocol or "http"

    def get_domain(self, site=None):
        # Determine domain
        if site is None:
            if django_apps.is_installed("django.contrib.sites"):
                Site = django_apps.get_model("sites.Site")
                try:
                    site = Site.objects.get_current()
                except Site.DoesNotExist:
                    pass
            if site is None:
                raise ImproperlyConfigured(
                    "To use sitemaps, either enable the sites framework or pass "
                    "a Site/RequestSite object in your view."
                )
        return site.domain

    def get_urls(self, page=1, site=None, protocol=None):
        protocol = self.get_protocol(protocol)
        domain = self.get_domain(site)
        return self._urls(page, protocol, domain)

    def get_latest_lastmod(self):
        if not hasattr(self, "lastmod"):
            return None
        if callable(self.lastmod):
            try:
                return max([self.lastmod(item) for item in self.items()])
            except TypeError:
                return None
        else:
            return self.lastmod

    def _urls(self, page, protocol, domain):
        urls = []
        latest_lastmod = None
        all_items_lastmod = True  # track if all items have a lastmod

        paginator_page = self.paginator.page(page)
        for item in paginator_page.object_list:
            loc = f"{protocol}://{domain}{self._location(item)}"
            priority = self._get("priority", item)
            lastmod = self._get("lastmod", item)

            if all_items_lastmod:
                all_items_lastmod = lastmod is not None
                if all_items_lastmod and (
                    latest_lastmod is None or lastmod > latest_lastmod
                ):
                    latest_lastmod = lastmod

            url_info = {
                "item": item,
                "location": loc,
                "lastmod": lastmod,
                "changefreq": self._get("changefreq", item),
                "priority": str(priority if priority is not None else ""),
                "alternates": [],
            }

            if self.i18n and self.alternates:
                for lang_code in self._languages():
                    loc = f"{protocol}://{domain}{self._location(item, lang_code)}"
                    url_info["alternates"].append(
                        {
                            "location": loc,
                            "lang_code": lang_code,
                        }
                    )
                if self.x_default:
                    lang_code = settings.LANGUAGE_CODE
                    loc = f"{protocol}://{domain}{self._location(item, lang_code)}"
                    loc = loc.replace(f"/{lang_code}/", "/", 1)
                    url_info["alternates"].append(
                        {
                            "location": loc,
                            "lang_code": "x-default",
                        }
                    )

            urls.append(url_info)

        if all_items_lastmod and latest_lastmod:
            self.latest_lastmod = latest_lastmod

        return urls


class GenericSitemap(Sitemap):
    priority = None
    changefreq = None

    def __init__(self, info_dict, priority=None, changefreq=None, protocol=None):
        self.queryset = info_dict["queryset"]
        self.date_field = info_dict.get("date_field")
        self.priority = self.priority or priority
        self.changefreq = self.changefreq or changefreq
        self.protocol = self.protocol or protocol

    def items(self):
        # Make sure to return a clone; we don't want premature evaluation.
        return self.queryset.filter()

    def lastmod(self, item):
        if self.date_field is not None:
            return getattr(item, self.date_field)
        return None

    def get_latest_lastmod(self):
        if self.date_field is not None:
            return (
                self.queryset.order_by("-" + self.date_field)
                .values_list(self.date_field, flat=True)
                .first()
            )
        return None
