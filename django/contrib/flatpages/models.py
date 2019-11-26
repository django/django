from django.contrib.sites.models import Site
from django.db import models
from django.urls import NoReverseMatch, get_script_prefix, reverse
from django.utils.encoding import iri_to_uri
from django.utils.translation import gettext_lazy as _


class FlatPage(models.Model):
    url = models.CharField(_('URL'), max_length=100, db_index=True)
    title = models.CharField(_('title'), max_length=200)
    content = models.TextField(_('content'), blank=True)
    enable_comments = models.BooleanField(_('enable comments'), default=False)
    template_name = models.CharField(
        _('template name'),
        max_length=70,
        blank=True,
        help_text=_(
            'Example: “flatpages/contact_page.html”. If this isn’t provided, '
            'the system will use “flatpages/default.html”.'
        ),
    )
    registration_required = models.BooleanField(
        _('registration required'),
        help_text=_("If this is checked, only logged-in users will be able to view the page."),
        default=False,
    )
    sites = models.ManyToManyField(Site, verbose_name=_('sites'))

    class Meta:
        db_table = 'django_flatpage'
        verbose_name = _('flat page')
        verbose_name_plural = _('flat pages')
        ordering = ['url']

    def __str__(self):
        return "%s -- %s" % (self.url, self.title)

    def get_absolute_url(self):
        from .views import flatpage

        for url in (self.url.lstrip('/'), self.url):
            try:
                return reverse(flatpage, kwargs={'url': url})
            except NoReverseMatch:
                pass
        # Handle script prefix manually because we bypass reverse()
        return iri_to_uri(get_script_prefix().rstrip('/') + self.url)
