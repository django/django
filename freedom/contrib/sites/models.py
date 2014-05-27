from __future__ import unicode_literals

import string
import warnings

from freedom.core.exceptions import ImproperlyConfigured, ValidationError
from freedom.db import models
from freedom.db.models.signals import pre_save, pre_delete
from freedom.utils.deprecation import RemovedInFreedom19Warning
from freedom.utils.encoding import python_2_unicode_compatible
from freedom.utils.translation import ugettext_lazy as _

from .requests import RequestSite as RealRequestSite
from .shortcuts import get_current_site as real_get_current_site


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


class SiteManager(models.Manager):

    def get_current(self):
        """
        Returns the current ``Site`` based on the SITE_ID in the
        project's settings. The ``Site`` object is cached the first
        time it's retrieved from the database.
        """
        from freedom.conf import settings
        try:
            sid = settings.SITE_ID
        except AttributeError:
            raise ImproperlyConfigured(
                "You're using the Freedom \"sites framework\" without having "
                "set the SITE_ID setting. Create a site in your database and "
                "set the SITE_ID setting to fix this error.")
        try:
            current_site = SITE_CACHE[sid]
        except KeyError:
            current_site = self.get(pk=sid)
            SITE_CACHE[sid] = current_site
        return current_site

    def clear_cache(self):
        """Clears the ``Site`` object cache."""
        global SITE_CACHE
        SITE_CACHE = {}


@python_2_unicode_compatible
class Site(models.Model):

    domain = models.CharField(_('domain name'), max_length=100,
        validators=[_simple_domain_name_validator])
    name = models.CharField(_('display name'), max_length=50)
    objects = SiteManager()

    class Meta:
        db_table = 'freedom_site'
        verbose_name = _('site')
        verbose_name_plural = _('sites')
        ordering = ('domain',)

    def __str__(self):
        return self.domain


class RequestSite(RealRequestSite):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Please import RequestSite from freedom.contrib.sites.requests.",
            RemovedInFreedom19Warning, stacklevel=2)
        super(RequestSite, self).__init__(*args, **kwargs)


def get_current_site(request):
    warnings.warn(
        "Please import get_current_site from freedom.contrib.sites.shortcuts.",
        RemovedInFreedom19Warning, stacklevel=2)
    return real_get_current_site(request)


def clear_site_cache(sender, **kwargs):
    """
    Clears the cache (if primed) each time a site is saved or deleted
    """
    instance = kwargs['instance']
    try:
        del SITE_CACHE[instance.pk]
    except KeyError:
        pass
pre_save.connect(clear_site_cache, sender=Site)
pre_delete.connect(clear_site_cache, sender=Site)
