from django.db import models
from django.contrib.sites.models import Site
from django.utils.translation import gettext_lazy as _

class Redirect(models.Model):
    site = models.ForeignKey(Site, radio_admin=models.VERTICAL)
    old_path = models.CharField(_('redirect from'), maxlength=200, db_index=True,
        help_text=_("This should be an absolute path, excluding the domain name. Example: '/events/search/'."))
    new_path = models.CharField(_('redirect to'), maxlength=200, blank=True,
        help_text=_("This can be either an absolute path (as above) or a full URL starting with 'http://'."))

    class Meta:
        verbose_name = _('redirect')
        verbose_name_plural = _('redirects')
        db_table = 'django_redirect'
        unique_together=(('site', 'old_path'),)
        ordering = ('old_path',)

    def __str__(self):
        return "%s ---> %s" % (self.old_path, self.new_path)

# Register the admin options for these models.
# TODO: Maybe this should live in a separate module admin.py, but how would we
# ensure that module was loaded?

from django.contrib import admin

class RedirectAdmin(admin.ModelAdmin):
    list_filter = ('site',)
    search_fields = ('old_path', 'new_path')

admin.site.register(Redirect, RedirectAdmin)
