from django.core import validators
from django.db import models
from django.models.core import Site
from django.utils.translation import gettext_lazy as _

class FlatPage(models.Model):
    url = models.CharField(_('URL'), maxlength=100, validator_list=[validators.isAlphaNumericURL],
        help_text=_("Example: '/about/contact/'. Make sure to have leading and trailing slashes."))
    title = models.CharField(_('title'), maxlength=200)
    content = models.TextField(_('content'))
    enable_comments = models.BooleanField(_('enable comments'))
    template_name = models.CharField(_('template name'), maxlength=70, blank=True,
        help_text=_("Example: 'flatpages/contact_page'. If this isn't provided, the system will use 'flatpages/default'."))
    registration_required = models.BooleanField(_('registration required'), help_text=_("If this is checked, only logged-in users will be able to view the page."))
    sites = models.ManyToManyField(Site)
    class Meta:
        db_table = 'django_flatpages'
        verbose_name = _('flat page')
        verbose_name_plural = _('flat pages')
        ordering = ('url',)
        admin = models.Admin(
            fields = (
                (None, {'fields': ('url', 'title', 'content', 'sites')}),
                ('Advanced options', {'classes': 'collapse', 'fields': ('enable_comments', 'registration_required', 'template_name')}),
            ),
            list_filter = ('sites',),
            search_fields = ('url', 'title'),
        )

    def __repr__(self):
        return "%s -- %s" % (self.url, self.title)

    def get_absolute_url(self):
        return self.url
