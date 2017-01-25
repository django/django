from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.signals import pre_delete, pre_save
from django.http.request import split_domain_port

from .base_site import AbstractBaseSite

__all__ = ('Site', 'SiteManager')


SITE_CACHE = {}


class SiteManager(models.Manager):
    use_in_migrations = True

    def _get_site_by_id(self, site_id):
        if site_id not in SITE_CACHE:
            site = self.get(pk=site_id)
            SITE_CACHE[site_id] = site
        return SITE_CACHE[site_id]

    def _get_site_by_request(self, request):
        host = request.get_host()
        try:
            # First attempt to look up the site by host with or without port.
            if host not in SITE_CACHE:
                SITE_CACHE[host] = self.get(domain__iexact=host)
            return SITE_CACHE[host]
        except self.model.DoesNotExist:
            # Fallback to looking up site after stripping port from the host.
            domain, port = split_domain_port(host)
            if domain not in SITE_CACHE:
                SITE_CACHE[domain] = self.get(domain__iexact=domain)
            return SITE_CACHE[domain]

    def get_current(self, request=None):
        """
        Returns the current Site based on the SITE_ID in the project's settings.
        If SITE_ID isn't defined, it returns the site with domain matching
        request.get_host(). The ``Site`` object is cached the first time it's
        retrieved from the database.
        """
        from django.conf import settings
        if getattr(settings, 'SITE_ID', ''):
            site_id = settings.SITE_ID
            return self._get_site_by_id(site_id)
        elif request:
            return self._get_site_by_request(request)

        raise ImproperlyConfigured(
            "You're using the Django \"sites framework\" without having "
            "set the SITE_ID setting. Create a site in your database and "
            "set the SITE_ID setting or pass a request to "
            "Site.objects.get_current() to fix this error."
        )

    def clear_cache(self):
        """Clears the ``Site`` object cache."""
        global SITE_CACHE
        SITE_CACHE = {}

    def get_by_natural_key(self, domain):
        return self.get(domain=domain)


class Site(AbstractBaseSite):
    """
    Sites within the Django sites app are represented by this
    model.

    Domain and name are required.
    """
    objects = SiteManager()

    class Meta(AbstractBaseSite.Meta):
        db_table = 'django_site'
        swappable = 'SITES_SITE_MODEL'


def clear_site_cache(sender, **kwargs):
    """
    Clears the cache (if primed) each time a site is saved or deleted
    """
    instance = kwargs['instance']
    using = kwargs['using']
    try:
        del SITE_CACHE[instance.pk]
    except KeyError:
        pass
    try:
        del SITE_CACHE[Site.objects.using(using).get(pk=instance.pk).domain]
    except (KeyError, Site.DoesNotExist):
        pass


pre_save.connect(clear_site_cache, sender=Site)
pre_delete.connect(clear_site_cache, sender=Site)
