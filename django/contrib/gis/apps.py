from django.apps import AppConfig
from django.core import checks, serializers
from django.utils.translation import gettext_lazy as _

from .checks import check_gdal_39


class GISConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "django.contrib.gis"
    verbose_name = _("GIS")

    def ready(self):
        serializers.BUILTIN_SERIALIZERS.setdefault(
            "geojson", "django.contrib.gis.serializers.geojson"
        )
        checks.register(check_gdal_39, checks.Tags.gis, checks.Tags.security)
