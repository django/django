from thibaud.apps import AppConfig
from thibaud.core import serializers
from thibaud.utils.translation import gettext_lazy as _


class GISConfig(AppConfig):
    default_auto_field = "thibaud.db.models.AutoField"
    name = "thibaud.contrib.gis"
    verbose_name = _("GIS")

    def ready(self):
        serializers.BUILTIN_SERIALIZERS.setdefault(
            "geojson", "thibaud.contrib.gis.serializers.geojson"
        )
