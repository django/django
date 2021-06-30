from mango.apps import AppConfig
from mango.core import serializers
from mango.utils.translation import gettext_lazy as _


class GISConfig(AppConfig):
    default_auto_field = 'mango.db.models.AutoField'
    name = 'mango.contrib.gis'
    verbose_name = _("GIS")

    def ready(self):
        serializers.BUILTIN_SERIALIZERS.setdefault('geojson', 'mango.contrib.gis.serializers.geojson')
