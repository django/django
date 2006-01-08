from django.db import models
from django.utils.translation import gettext_lazy as _

class SiteManager(models.Manager):
    def get_current(self):
        from django.conf.settings import SITE_ID
        return self.get_object(pk=SITE_ID)

class Site(models.Model):
    domain = models.CharField(_('domain name'), maxlength=100)
    name = models.CharField(_('display name'), maxlength=50)
    objects = SiteManager()
    class Meta:
        verbose_name = _('site')
        verbose_name_plural = _('sites')
        ordering = ('domain',)
    class Admin:
        list_display = ('domain', 'name')
        search_fields = ('domain', 'name')

    def __repr__(self):
        return self.domain
