from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AdminDocsConfig(AppConfig):
    name = 'django.contrib.admindocs'
    verbose_name = _("Administrative Documentation")
