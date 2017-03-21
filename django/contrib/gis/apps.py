from django.apps import AppConfig
from django.core import serializers
from django.utils.translation import gettext_lazy as _


class GISConfig(AppConfig):
    name = 'django.contrib.gis'
    verbose_name = _("GIS")

    def ready(self):
        if 'geojson' not in serializers.BUILTIN_SERIALIZERS:
            serializers.BUILTIN_SERIALIZERS['geojson'] = "django.contrib.gis.serializers.geojson"
