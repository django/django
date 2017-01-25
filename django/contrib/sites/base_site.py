from django.contrib.sites.validators import _simple_domain_name_validator
from django.db import models
from django.utils.translation import ugettext_lazy as _


class AbstractBaseSite(models.Model):
    """
    An abstract base class implementing a fully featured Site model.

    Domain and name are required.
    """
    domain = models.CharField(
        _('domain name'),
        max_length=100,
        validators=[_simple_domain_name_validator],
        unique=True,
    )
    name = models.CharField(_('display name'), max_length=50)

    class Meta:
        abstract = True
        verbose_name = _('site')
        verbose_name_plural = _('sites')
        ordering = ('domain',)

    def __str__(self):
        return self.domain

    def natural_key(self):
        return (self.domain,)
