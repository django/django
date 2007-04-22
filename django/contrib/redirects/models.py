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

    class Admin:
        list_filter = ('site',)
        search_fields = ('old_path', 'new_path')

    def __unicode__(self):
        return u"%s ---> %s" % (self.old_path, self.new_path)
