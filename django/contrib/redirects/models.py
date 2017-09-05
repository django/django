from django.db import models
from django.utils.translation import gettext_lazy as _


class Redirect(models.Model):
    domain = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('domain'),
        help_text=_('If set, redirect requests from this domain only.'),
    )

    old_path = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name=_('redirect from'),
        help_text=_("This should be an absolute path, excluding the domain name. Example: '/events/search/'."),
    )
    new_path = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('redirect to'),
        help_text=_("This can be either an absolute path (as above) or a full URL starting with 'http://'."),
    )

    class Meta:
        verbose_name = _('redirect')
        verbose_name_plural = _('redirects')
        db_table = 'django_redirect'
        unique_together = ('old_path', 'domain')
        ordering = ('old_path',)

    def __str__(self):
        return "%s%s ---> %s" % (self.domain, self.old_path, self.new_path)
