# -*- coding: utf-8 -*-
"""
Models for {{ app_name|title }} Django application.

.. seealso::
    http://docs.djangoproject.com/en/dev/ref/models/fields/
"""
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User


# Replace the following example with your models.

class {{ app_name|title }}(models.Model):
    """Model for {{ app_name }}s."""

    name = models.CharField(_('name'), max_length=20)
    category = models.CharField(_('category'), blank=True, max_length=20)
    user = models.ManyToManyField(User, verbose_name=_('user'), blank=True)
    date_modified = models.DateTimeField(_('last modification date'),
        auto_now=True, auto_now_add=True)

    class Meta:
        verbose_name = _('{{ app_name|title }}')
        verbose_name_plural = _('{{ app_name|title }}s')
        ordering = ('name',)

    def __unicode__(self):
        return u'{0}'.format(self.name)

