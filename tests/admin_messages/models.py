from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class HTMLTag(models.Model):

    name = models.CharField(_("name"), max_length=20, unique=True)

    def __str__(self):
        return "<{}>".format(self.name)

    class Meta:
        verbose_name = _("HTML tag")
        verbose_name_plural = _("HTML tags")
