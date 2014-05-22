from django.apps import AppConfig

from django.contrib.gis.db.models.fields import GeometryField
from django.contrib.gis.db.models.lookups import gis_lookups
from django.utils.translation import ugettext_lazy as _


class GISConfig(AppConfig):
    name = 'django.contrib.gis'
    verbose_name = _("GIS")

    def ready(self):
        # GIS Lookups registration
        for name, klass in gis_lookups.items():
            GeometryField.register_lookup(klass)
