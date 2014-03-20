from django.apps import AppConfig

from django.utils.translation import ugettext_lazy as _


class GISConfig(AppConfig):
    name = 'django.contrib.gis'
    verbose_name = _("GIS")
