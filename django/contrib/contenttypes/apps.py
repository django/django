from django.apps import AppConfig

from django.utils.translation import ugettext_lazy as _


class ContentTypesConfig(AppConfig):
    name = 'django.contrib.contenttypes'
    verbose_name = _("content types")
