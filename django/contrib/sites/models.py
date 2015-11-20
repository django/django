from __future__ import unicode_literals

import string

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.db.models.signals import post_save, pre_delete, pre_save
from django.http.request import split_domain_port
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

SITE_CACHE = {}


def _simple_domain_name_validator(value):
    """
    Validates that the given value contains no whitespaces to prevent common
    typos.
    """
    if not value:
        return
    checks = ((s in value) for s in string.whitespace)
    if any(checks):
        raise ValidationError(
            _("The domain name cannot contain any spaces or tabs."),
            code='invalid',
        )


def _cache_key_for_site_id(site_id):
    return 'site:id:%s' % (site_id,)


def _cache_key_for_site_host(site_host):
    return 'site:host:%s' % (site_host,)


class SiteManager(models.Manager):
    use_in_migrations = True

    def _get_site_by_id(self, site_id):
        key = _cache_key_for_site_id(site_id)
        site = cache.get(key)
        if site is None:
            site = self.get(pk=site_id)
            SITE_CACHE[site_id] = site
        cache.add(key, site)
        return site

    def _get_site_by_request(self, request):
        host = request.get_host()
        key = _cache_key_for_site_host(host)
        site = cache.get(key)
        if site is None:
            try:
                # First attempt to look up the site by host with or without port.
                site = self.get(domain__iexact=host)
            except Site.DoesNotExist:
                # Fallback to looking up site after stripping port from the host.
                domain, port = split_domain_port(host)
                if not port:
                    raise
                site = self.get(domain__iexact=domain)
            SITE_CACHE[host] = site
        cache.add(key, site)
        return site

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
        keys_id = [_cache_key_for_site_id(site_id) for site_id in SITE_CACHE]
        keys_host = [_cache_key_for_site_host(site_host) for site_host in SITE_CACHE]
        cache.delete_many(keys_id + keys_host)
        SITE_CACHE.clear()

    def get_by_natural_key(self, domain):
        return self.get(domain=domain)


@python_2_unicode_compatible
class Site(models.Model):

    domain = models.CharField(_('domain name'), max_length=100,
        validators=[_simple_domain_name_validator], unique=True)
    name = models.CharField(_('display name'), max_length=50)
    objects = SiteManager()

    class Meta:
        db_table = 'django_site'
        verbose_name = _('site')
        verbose_name_plural = _('sites')
        ordering = ('domain',)

    def __str__(self):
        return self.domain

    def natural_key(self):
        return (self.domain,)


def clear_site_cache(sender, **kwargs):
    """
    Clears the cache (if primed) each time a site is saved or deleted
    """
    instance = kwargs['instance']
    key_id = _cache_key_for_site_id(instance.pk)
    key_host = _cache_key_for_site_host(instance.domain)
    cache.delete_many([key_id, key_host])
    try:
        del SITE_CACHE[instance.pk]
    except KeyError:
        pass
    try:
        del SITE_CACHE[instance.domain]
    except KeyError:
        pass
pre_save.connect(clear_site_cache, sender=Site)
post_save.connect(clear_site_cache, sender=Site)
pre_delete.connect(clear_site_cache, sender=Site)
