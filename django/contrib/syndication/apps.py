from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SyndicationConfig(AppConfig):
    name = 'django.contrib.syndication'
    verbose_name = _("Syndication")
